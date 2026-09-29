"""CSV ingest: 1..n files → DatasetSchema with profiles, PK/FK guesses and rules.

Values are read as strings and typed by `heuristics`, so "00123" stays a
code and "$1,200.00" becomes a decimal. The rows are profiled and then
dropped; only aggregates reach the AI (see `enrich`).
"""

import io
import re

import pandas as pd

from app.core.exceptions import AppError
from app.ingest.build import RawTable, column_from_values, finalize
from app.ingest.enrich import enrich_schema
from app.ingest.heuristics import is_id_name
from app.ingest.profiler import children_distribution
from app.ingest.rules import infer_rules
from app.schemas.dataset import DatasetSchema, ForeignKey

MAX_FILES = 10
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_ROWS = 200_000
FK_MATCH_RATE = 0.9  # share of child values that must exist in the parent key


class CsvError(AppError):
    code = "invalid_csv"
    status_code = 400


async def ingest_csv(files: list[tuple[str, bytes]]) -> tuple[DatasetSchema, list[str]]:
    if not files:
        raise CsvError("Upload at least one CSV file.")
    if len(files) > MAX_FILES:
        raise CsvError(f"Upload at most {MAX_FILES} CSV files at once.")

    frames: dict[str, pd.DataFrame] = {}
    for filename, content in files:
        name = _table_name(filename, frames)
        frames[name] = _read(filename, content)

    raw_tables, notes = _raw_tables(frames)
    schema, build_notes = finalize(raw_tables, "csv", _dataset_name(frames))
    notes += build_notes
    notes += await enrich_schema(schema)
    schema.rules = infer_rules(schema, frames)
    if schema.rules:
        notes.append(f"Found {len(schema.rules)} rule(s) that hold for every uploaded row.")
    return schema, notes


def _read(filename: str, content: bytes) -> pd.DataFrame:
    label = _safe_label(filename)
    if len(content) > MAX_FILE_BYTES:
        raise CsvError(f"{label} is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB.")
    if not content.strip():
        raise CsvError(f"{label} is empty.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    try:
        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=True, sep=None, engine="python", nrows=MAX_ROWS)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeError, ValueError, TypeError):
        raise CsvError(f"{label} could not be read as CSV.") from None
    df.columns = [_column_name(c, i) for i, c in enumerate(df.columns)]
    df = df.loc[:, ~df.columns.duplicated()]
    if df.empty or len(df.columns) == 0:
        raise CsvError(f"{label} has a header but no data rows.")
    return df


def _raw_tables(frames: dict[str, pd.DataFrame]) -> tuple[list[RawTable], list[str]]:
    notes: list[str] = []
    raw: list[RawTable] = []
    for name, df in frames.items():
        columns = [column_from_values(c, df[c]) for c in df.columns]
        raw.append(RawTable(name=name, columns=columns, primary_key=_guess_pk(name, df), row_count=len(df)))

    pks = {rt.name: rt.primary_key for rt in raw if rt.primary_key}
    for rt in raw:
        df = frames[rt.name]
        for col in df.columns:
            if col == rt.primary_key or not is_id_name(col):
                continue
            parent = _guess_parent(col, rt.name, pks, frames)
            if parent is None:
                continue
            parent_pk = pks[parent]
            dist = children_distribution(df[col], frames[parent][parent_pk])
            rt.foreign_keys.append(ForeignKey(column=col, ref_table=parent, ref_column=parent_pk, children_distribution=dist))
            notes.append(f"Linked {rt.name}.{col} → {parent}.{parent_pk} (matching names and values).")
    return raw, notes


def _guess_pk(table: str, df: pd.DataFrame) -> str | None:
    singular = _singular(table)
    for c in ("id", f"{singular}_id", f"{table}_id"):
        if c in df.columns and _is_key(df[c]):
            return c
    # otherwise only the first column, so a unique FK column (1:1 child) is not taken as the PK
    first = df.columns[0]
    return first if _is_key(df[first]) and (is_id_name(first) or first.endswith(("_no", "_number", "_code"))) else None


def _is_key(s: pd.Series) -> bool:
    return s.notna().all() and s.is_unique and len(s) > 0


def _guess_parent(col: str, table: str, pks: dict[str, str], frames: dict[str, pd.DataFrame]) -> str | None:
    """`customer_id` → the table whose PK is `customer_id`, or table `customers` with PK `id`."""
    stem = re.sub(r"[_-]?id$", "", col, flags=re.I).lower()
    matches = [p for p, pk in pks.items() if p != table and (pk.lower() == col.lower() or (pk.lower() == "id" and _singular(p) == stem))]
    for parent in matches:
        child_vals = frames[table][col].dropna().astype(str)
        parent_vals = set(frames[parent][pks[parent]].astype(str))
        if child_vals.empty or child_vals.isin(parent_vals).mean() >= FK_MATCH_RATE:
            return parent
    return None


def _singular(name: str) -> str:
    n = name.lower()
    if n.endswith("ies"):
        return n[:-3] + "y"
    if n.endswith(("ses", "xes")):
        return n[:-2]
    return n[:-1] if n.endswith("s") and not n.endswith("ss") else n


def _table_name(filename: str, existing: dict) -> str:
    stem = re.sub(r"\.(csv|txt|tsv)$", "", (filename or "table").rsplit("/", 1)[-1].rsplit("\\", 1)[-1], flags=re.I)
    name = _slug(stem) or "table"
    if name[0].isdigit():
        name = f"t_{name}"
    base, i = name, 2
    while name in existing:
        name, i = f"{base}_{i}", i + 1
    return name


def _column_name(raw: object, index: int) -> str:
    name = _slug(str(raw))
    if not name or name.startswith("unnamed"):
        name = f"column_{index + 1}"
    return f"c_{name}" if name[0].isdigit() else name


def _slug(text: str) -> str:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text.strip())  # camelCase → snake_case
    return "_".join(re.sub(r"[^0-9a-zA-Z]+", " ", text).lower().split())


def _safe_label(filename: str) -> str:
    return re.sub(r"[^\w. -]", "", (filename or "file"))[:80] or "file"


def _dataset_name(frames: dict) -> str:
    return "csv_" + "_".join(list(frames)[:3]) if frames else "csv_schema"
