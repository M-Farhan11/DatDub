"""Postgres / SQLite introspection and sampling (steps A, B and C).

Step A (`list_tables`) reads catalog metadata only, never rows.
Steps B+C (`extract`) introspect the selected tables with SQLAlchemy
`inspect()`, auto-add FK parents, and in `schema_and_sample` mode read up
to `sample_limit` random rows per table, profile them, and drop them.
Children-per-parent counts are read as aggregates for the sampled parents,
and in sample mode catalogue rules are checked over whole tables with
aggregate queries (`db_rules`). All reads happen inside `db_guard.read_only`.
"""

import logging
import os
import tempfile
from dataclasses import dataclass

import pandas as pd
from sqlalchemy import bindparam, create_engine, inspect, text, types as satypes
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool
from starlette.concurrency import run_in_threadpool

from app.core.exceptions import AppError
from app.ingest.build import RawTable, column_from_metadata, column_from_values, finalize
from app.ingest.db_guard import make_engine, map_db_error, read_only
from app.ingest.db_rules import infer_db_rules
from app.ingest.enrich import enrich_schema
from app.ingest.profiler import counts_to_distribution
from app.schemas.api import DbConnection, DbTableInfo, ExtractMode, FromDbResponse
from app.schemas.dataset import DatasetSchema, DataType, ForeignKey, SourceKind

logger = logging.getLogger("app.ingest.db")

MAX_TABLES = 30
TABLESAMPLE_MIN_ROWS = 10_000  # below this, ORDER BY random() is cheap enough
MAX_SQLITE_BYTES = 50 * 1024 * 1024
SQLITE_MAGIC = b"SQLite format 3\x00"


@dataclass
class _Meta:
    name: str
    columns: list[dict]
    pk: list[str]
    fks: list[dict]
    estimated_rows: int
    unique: set[str]


# --- step A --------------------------------------------------------------------


def list_tables(conn: DbConnection) -> list[DbTableInfo]:
    engine = make_engine(conn)
    with read_only(engine) as c:
        insp = inspect(c)
        names = insp.get_table_names(schema="public")
        estimates = _pg_estimates(c)
        out = []
        for name in sorted(names):
            fks = insp.get_foreign_keys(name, schema="public")
            refs = sorted({fk["referred_table"] for fk in fks if fk.get("referred_table") and fk["referred_table"] != name})
            out.append(
                DbTableInfo(
                    name=name,
                    schema="public",
                    column_count=len(insp.get_columns(name, schema="public")),
                    estimated_rows=estimates.get(name, 0),
                    references=refs,
                )
            )
    return out


def _pg_estimates(c: Connection) -> dict[str, int]:
    rows = c.execute(
        text(
            "SELECT c.relname, c.reltuples::bigint FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')"
        )
    )
    return {name: max(int(est or 0), 0) for name, est in rows}  # reltuples is -1 before the first ANALYZE


# --- steps B + C -----------------------------------------------------------------


async def extract_postgres(conn: DbConnection, tables: list[str], mode: ExtractMode, sample_limit: int) -> FromDbResponse:
    engine = await run_in_threadpool(make_engine, conn)  # resolves DNS
    return await _extract(engine, "postgres", "public", tables, mode, sample_limit)


async def extract_sqlite(content: bytes, tables: list[str], mode: ExtractMode, sample_limit: int) -> FromDbResponse:
    if len(content) > MAX_SQLITE_BYTES:
        raise AppError("The SQLite file is larger than 50 MB.", code="invalid_sqlite_file", status_code=400)
    if not content.startswith(SQLITE_MAGIC):
        raise AppError("The uploaded file is not a SQLite database.", code="invalid_sqlite_file", status_code=400)
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        uri = "file:" + path.replace("\\", "/") + "?mode=ro"
        engine = create_engine("sqlite://", creator=lambda: _sqlite_connect(uri), poolclass=NullPool)
        return await _extract(engine, "sqlite", None, tables, mode, sample_limit)
    finally:
        try:
            os.remove(path)
        except OSError:
            logger.warning("Could not delete a temporary SQLite upload")


def _sqlite_connect(uri: str):
    import sqlite3

    return sqlite3.connect(uri, uri=True, check_same_thread=False)


async def _extract(
    engine: Engine, source: SourceKind, schema_name: str | None, tables: list[str], mode: ExtractMode, sample_limit: int
) -> FromDbResponse:
    # blocking DB I/O runs in a worker thread, the AI call back on the event loop
    schema, auto_added, rows_sampled, notes = await run_in_threadpool(
        _read_tables, engine, source, schema_name, tables, mode, sample_limit
    )
    notes += await enrich_schema(schema)
    if mode == "schema_only":
        notes.append("Schema only: column semantics come from names and types (no rows were read).")
    return FromDbResponse(schema=schema, auto_added=auto_added, rows_sampled=rows_sampled, notes=notes)


def _read_tables(
    engine: Engine, source: SourceKind, schema_name: str | None, tables: list[str], mode: ExtractMode, sample_limit: int
) -> tuple[DatasetSchema, list[str], int, list[str]]:
    wanted = list(dict.fromkeys(t.strip() for t in tables if t.strip()))
    samples: dict[str, pd.DataFrame] = {}
    distributions: dict[tuple[str, str], list[tuple[int, float]]] = {}
    notes: list[str] = []

    with read_only(engine) as c:
        insp = inspect(c)
        available = set(insp.get_table_names(schema=schema_name))
        if not wanted:
            wanted = sorted(available)
        missing = [t for t in wanted if t not in available]
        if missing:
            raise AppError(
                f"{len(missing)} selected table(s) were not found in the database.", code="table_not_found", status_code=404
            )
        estimates = _pg_estimates(c) if source == "postgres" else {}

        metas: dict[str, _Meta] = {}
        auto_added: list[str] = []
        queue = list(wanted)
        while queue:
            name = queue.pop(0)
            if name in metas:
                continue
            fks = insp.get_foreign_keys(name, schema=schema_name)
            metas[name] = _Meta(
                name=name,
                columns=insp.get_columns(name, schema=schema_name),
                pk=list(insp.get_pk_constraint(name, schema=schema_name).get("constrained_columns") or []),
                fks=fks,
                estimated_rows=estimates.get(name, 0),
                unique=_unique_columns(insp, name, schema_name),
            )
            for fk in fks:
                parent = fk.get("referred_table")
                if parent and parent in available and parent not in metas and parent not in queue:
                    queue.append(parent)
                    if parent not in wanted:
                        auto_added.append(parent)
        if len(metas) > MAX_TABLES:
            raise AppError(f"Select at most {MAX_TABLES} tables (including referenced parents).", code="validation_error", status_code=422)

        if source == "sqlite":
            for m in metas.values():
                m.estimated_rows = c.execute(text(f"SELECT COUNT(*) FROM {_q(c, m.name)}")).scalar() or 0

        if mode == "schema_and_sample":
            for m in metas.values():
                samples[m.name] = _sample(c, source, schema_name, m, sample_limit)
            for m in metas.values():
                for fk in _single_fks(m):
                    parent_pk = _single_pk(metas.get(fk["referred_table"]))
                    parent_sample = samples.get(fk["referred_table"])
                    if parent_pk and parent_sample is not None and parent_pk in parent_sample:
                        dist = _children_counts(c, schema_name, m.name, fk["constrained_columns"][0], parent_sample[parent_pk])
                        if dist is None:
                            notes.append(f"Skipped the {m.name} per-{fk['referred_table']} distribution (query too slow).")
                        elif dist:
                            distributions[(m.name, fk["constrained_columns"][0])] = dist

        raw = [_raw_table(m, samples.get(m.name), distributions, notes) for m in metas.values()]
        rows_sampled = sum(len(df) for df in samples.values())
        samples.clear()  # rows are profiled; drop them before any AI call
        schema, build_notes = finalize(raw, source, f"{source}_schema")
        notes += build_notes
        if mode == "schema_and_sample":
            links = {
                (m.name, fk["constrained_columns"][0]): (fk["referred_table"], fk["referred_columns"][0])
                for m in metas.values()
                for fk in _single_fks(m)
            }
            schema.rules, rule_notes = infer_db_rules(c, schema_name, schema, links)
            notes += rule_notes
    return schema, auto_added, rows_sampled, notes


def _raw_table(m: _Meta, sample: pd.DataFrame | None, dists: dict, notes: list[str]) -> RawTable:
    columns = []
    for col in m.columns:
        data_type = sql_type_to_data_type(col["type"])
        nullable = bool(col.get("nullable", True))
        if sample is not None and col["name"] in sample:
            columns.append(column_from_values(col["name"], sample[col["name"]], declared=data_type, nullable=nullable))
        else:
            columns.append(column_from_metadata(col["name"], data_type, nullable))
    for col in columns:
        if col.name in m.unique:
            # a sampled range is too narrow for many distinct values: keep only the lower bound
            col.unique, col.max = True, None
    pk = m.pk[0] if m.pk else None
    if len(m.pk) > 1:
        notes.append(f"{m.name} has a composite primary key; the generator uses a single generated key instead.")
        pk = None
    fks = [
        ForeignKey(
            column=fk["constrained_columns"][0],
            ref_table=fk["referred_table"],
            ref_column=fk["referred_columns"][0],
            children_distribution=dists.get((m.name, fk["constrained_columns"][0])),
            cardinality="1:1" if fk["constrained_columns"][0] in m.unique else "1:N",
        )
        for fk in _single_fks(m)
    ]
    if len(fks) < len(m.fks):
        notes.append(f"{m.name}: composite foreign keys are not supported and were skipped.")
    return RawTable(name=m.name, columns=columns, primary_key=pk, foreign_keys=fks, row_count=m.estimated_rows or None)


def _unique_columns(insp, name: str, schema_name: str | None) -> set[str]:
    """Columns with a single-column UNIQUE constraint or unique index."""
    groups = [u.get("column_names") or [] for u in insp.get_unique_constraints(name, schema=schema_name)]
    groups += [i.get("column_names") or [] for i in insp.get_indexes(name, schema=schema_name) if i.get("unique")]
    return {g[0] for g in groups if len(g) == 1 and g[0]}


def _single_fks(m: _Meta) -> list[dict]:
    return [
        fk for fk in m.fks
        if fk.get("referred_table") and len(fk.get("constrained_columns") or []) == 1 and len(fk.get("referred_columns") or []) == 1
    ]


def _single_pk(m: _Meta | None) -> str | None:
    return m.pk[0] if m and len(m.pk) == 1 else None


def _q(c: Connection, name: str, schema_name: str | None = None) -> str:
    prep = c.dialect.identifier_preparer
    return f"{prep.quote_identifier(schema_name)}.{prep.quote_identifier(name)}" if schema_name else prep.quote_identifier(name)


def _sample(c: Connection, source: SourceKind, schema_name: str | None, m: _Meta, limit: int) -> pd.DataFrame:
    table = _q(c, m.name, schema_name)
    if source == "postgres" and m.estimated_rows >= TABLESAMPLE_MIN_ROWS:
        # read ~3x the needed share of pages, then trim; SYSTEM sampling is block-level and fast
        pct = min(100.0, max(0.01, limit * 3 * 100.0 / m.estimated_rows))
        sql = f"SELECT * FROM {table} TABLESAMPLE SYSTEM ({pct:.4f}) LIMIT {int(limit)}"
    else:
        sql = f"SELECT * FROM {table} ORDER BY random() LIMIT {int(limit)}"
    result = c.execute(text(sql))
    df = pd.DataFrame(result.fetchall(), columns=list(result.keys()))
    for col in df.columns:  # json/array values are unhashable; profile them as text
        if df[col].dtype == object and df[col].map(lambda v: isinstance(v, (dict, list, bytes, bytearray, memoryview))).any():
            df[col] = df[col].map(lambda v: None if v is None else str(v))
    return df


def _children_counts(
    c: Connection, schema_name: str | None, child: str, fk_col: str, parent_keys: pd.Series
) -> list[tuple[int, float]] | None:
    """Children per sampled parent, read as one GROUP BY (no child rows leave the database)."""
    keys = [k for k in parent_keys.dropna().tolist()]
    if not keys:
        return []
    col = c.dialect.identifier_preparer.quote_identifier(fk_col)
    stmt = text(f"SELECT {col}, COUNT(*) FROM {_q(c, child, schema_name)} WHERE {col} IN :keys GROUP BY {col}").bindparams(
        bindparam("keys", expanding=True)
    )
    try:
        with c.begin_nested():  # a timeout here must not abort the whole extract
            counts = {str(k): int(n) for k, n in c.execute(stmt, {"keys": keys})}
    except DBAPIError as exc:
        err = map_db_error(exc)
        if err.code == "db_timeout":
            return None
        raise err from None
    return counts_to_distribution(pd.Series([counts.get(str(k), 0) for k in keys]).to_numpy())


def sql_type_to_data_type(sql_type: satypes.TypeEngine) -> DataType:
    if isinstance(sql_type, satypes.Boolean):
        return "boolean"
    if isinstance(sql_type, satypes.Integer):
        return "integer"
    if isinstance(sql_type, satypes.Numeric):
        return "float" if isinstance(sql_type, satypes.Float) else "decimal"
    if isinstance(sql_type, satypes.DateTime):
        return "datetime"
    if isinstance(sql_type, satypes.Date):
        return "date"
    try:
        py = sql_type.python_type
    except (NotImplementedError, AttributeError):
        return "string"
    return {bool: "boolean", int: "integer", float: "float"}.get(py, "string")

