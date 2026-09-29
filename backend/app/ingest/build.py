"""Shared last step of every ingest path: raw tables → a valid DatasetSchema.

CSV, Postgres and SQLite ingest each produce `RawTable`s; `finalize`
makes them contract-valid the same way `draft_to_schema` does for AI
output: every table has a string PK, FKs point at an existing parent's PK,
self-references and cycles are dropped, and child counts come from the
sampled children-per-parent distribution when there is one.
"""

from dataclasses import dataclass, field

import pandas as pd

from app.ai.validate import MAX_CHILDREN_CAP, invoice_hints
from app.ingest.heuristics import infer_column, is_pii_semantic, name_semantics
from app.ingest.profiler import profile_column
from app.schemas.dataset import ColumnSchema, DatasetSchema, DataType, ForeignKey, SourceKind, TableSchema

ROW_COUNT_HINT_CAP = 1000  # default generation size; the user can raise it in Configure


@dataclass
class RawTable:
    name: str
    columns: list[ColumnSchema]
    primary_key: str | None = None
    foreign_keys: list[ForeignKey] = field(default_factory=list)
    row_count: int | None = None


def column_from_values(name: str, raw: pd.Series, declared: DataType | None = None, nullable: bool | None = None) -> ColumnSchema:
    """Build a column from sample values. `declared` (a DB type) wins over the inferred type."""
    non_null = raw.dropna()
    if pd.api.types.is_string_dtype(raw) or raw.dtype == object:
        non_null = non_null[non_null.astype(str).str.strip() != ""]
    guess = infer_column(name, non_null)
    data_type = declared or guess.data_type
    semantic, confidence = guess.semantic_type, guess.confidence
    numeric = {"integer", "float", "decimal"}
    if declared and declared != guess.data_type and not {declared, guess.data_type} <= numeric:
        # e.g. a TEXT column holding numbers: trust the declared type, keep name semantics only
        by_name = name_semantics(name)
        if by_name and not (by_name[0] in ("currency_amount", "quantity", "percentage") and declared not in numeric):
            semantic, confidence = by_name[0], 0.8
        else:
            semantic, confidence = _default_semantic(declared), 0.5
    pii = guess.pii or is_pii_semantic(semantic)
    col = ColumnSchema(
        name=name,
        data_type=data_type,
        semantic_type=semantic,
        nullable=bool(raw.isna().any() or len(non_null) < len(raw)) if nullable is None else nullable,
        pii=pii,
        confidence=confidence,
    )
    col.profile = profile_column(raw, data_type, pii, guess.parsed if data_type == guess.data_type else None)
    _apply_profile_bounds(col)
    return col


def column_from_metadata(name: str, data_type: DataType, nullable: bool) -> ColumnSchema:
    """Schema-only mode: no values, so semantics come from the name alone."""
    by_name = name_semantics(name)
    semantic, pii, confidence = (*by_name, 0.7) if by_name else (_default_semantic(data_type), False, 0.4)
    if semantic in ("currency_amount", "quantity", "percentage") and data_type not in ("integer", "float", "decimal"):
        semantic, pii, confidence = "generic_string", False, 0.4
    return ColumnSchema(name=name, data_type=data_type, semantic_type=semantic, nullable=nullable, pii=pii, confidence=confidence)


def _default_semantic(data_type: DataType):
    if data_type in ("date", "datetime"):
        return data_type
    if data_type in ("integer", "float", "decimal"):
        return "generic_number"
    return "generic_string"


def _apply_profile_bounds(col: ColumnSchema) -> None:
    """Give the generator the sampled range and categories to work from."""
    p = col.profile
    if p is None:
        return
    if col.data_type in ("integer", "float", "decimal", "date", "datetime"):
        col.min, col.max = p.min, p.max
    elif p.top_values and not col.pii and col.semantic_type in ("category", "status") and len(p.top_values) <= 10:
        col.allowed_values = [v for v, _ in p.top_values]


def finalize(raw_tables: list[RawTable], source: SourceKind, name: str) -> tuple[DatasetSchema, list[str]]:
    notes: list[str] = []
    tables: list[TableSchema] = []
    for rt in raw_tables:
        pk_name = rt.primary_key
        if pk_name is None or not any(c.name == pk_name for c in rt.columns):
            pk_name = _synthetic_pk(rt)
            rt.columns.insert(0, ColumnSchema(name=pk_name, data_type="string", semantic_type="id"))
            notes.append(f"{rt.name} has no primary key; added a generated '{pk_name}' column.")
        _as_key(next(c for c in rt.columns if c.name == pk_name), primary=True)
        hint = min(rt.row_count, ROW_COUNT_HINT_CAP) if rt.row_count else None
        tables.append(TableSchema(name=rt.name, primary_key=pk_name, columns=rt.columns, row_count_hint=hint))

    by_name = {t.name: t for t in tables}
    parents: dict[str, set[str]] = {t.name: set() for t in tables}
    for rt in raw_tables:
        table = by_name[rt.name]
        for fk in rt.foreign_keys:
            parent = by_name.get(fk.ref_table)
            col = next((c for c in table.columns if c.name == fk.column), None)
            if parent is None or col is None:
                continue
            if parent.name == table.name:
                notes.append(f"Ignored self-reference {table.name}.{fk.column} (not supported by the generator).")
                continue
            if _reaches(parents, parent.name, table.name):
                notes.append(f"Ignored foreign key {table.name}.{fk.column}: it would create a cycle.")
                continue
            if any(f.column == fk.column for f in table.foreign_keys):
                continue
            if fk.ref_column != parent.primary_key:
                notes.append(
                    f"{table.name}.{fk.column} references {parent.name}.{fk.ref_column}; "
                    f"the generator links it to the primary key {parent.name}.{parent.primary_key}."
                )
            _as_key(col, primary=False)
            dist = fk.children_distribution
            if dist:
                fk.min_children = min(n for n, _ in dist)
                fk.max_children = max(1, min(max(n for n, _ in dist), MAX_CHILDREN_CAP))
                fk.min_children = min(fk.min_children, fk.max_children)
            fk.ref_column = parent.primary_key
            table.foreign_keys.append(fk)
            parents[table.name].add(parent.name)

    schema = DatasetSchema(name=name, source=source, tables=tables)
    schema.document_hints = invoice_hints(schema)
    return schema, notes


def _as_key(col: ColumnSchema, primary: bool) -> None:
    """Key columns hold engine-generated string ids (e.g. "INV-00001"), so drop sampled ranges/values."""
    col.data_type, col.semantic_type, col.pii, col.confidence = "string", "id", False, 1.0
    col.allowed_values, col.min, col.max = None, None, None
    if primary:
        col.unique, col.nullable = True, False
    if col.profile:
        col.profile.top_values = col.profile.histogram = None
        col.profile.mean = col.profile.std = col.profile.min = col.profile.max = None


def _synthetic_pk(rt: RawTable) -> str:
    base = rt.name[:-1] if rt.name.endswith("s") and len(rt.name) > 3 else rt.name
    candidate = f"{base}_id"
    names = {c.name for c in rt.columns}
    while candidate in names:
        candidate = f"_{candidate}"
    return candidate


def _reaches(parents: dict[str, set[str]], start: str, target: str) -> bool:
    stack, seen = [start], set()
    while stack:
        node = stack.pop()
        if node == target:
            return True
        if node not in seen:
            seen.add(node)
            stack.extend(parents.get(node, ()))
    return False
