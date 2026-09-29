"""ZIP export of a generated dataset. OWNER: Haider (H7).

Contents (docs/api-contract.md):
    tables/<table>.csv, tables/<table>.json, schema.json,
    validation_report.json, ground_truth.json,
    documents/invoices/<id>.pdf (first 20, only with document_hints.invoice),
    README.txt

Rows are formatted like the paged table endpoint (`to_records`): dates as
YYYY-MM-DD (datetimes as ISO), missing values as empty (CSV) / null (JSON).
The archive is written to a spooled temp file so large datasets do not have
to fit in memory.
"""

from __future__ import annotations

import json
import tempfile
import zipfile
from typing import BinaryIO

import pandas as pd

from app.documents.invoice_pdf import invoice_pdf_bytes
from app.engine.store import GeneratedDataset

MAX_INVOICE_PDFS = 20
# Keep up to 64 MB in memory, spill to disk above that.
SPOOL_BYTES = 64 * 1024 * 1024


def _formatted(df: pd.DataFrame) -> pd.DataFrame:
    """Same date formatting as `app.engine.generator.to_records`."""
    out = df.copy()
    for name in out.columns:
        s = out[name]
        if pd.api.types.is_datetime64_any_dtype(s):
            has_time = bool((s.dropna() != s.dropna().dt.normalize()).any())
            out[name] = s.dt.strftime("%Y-%m-%dT%H:%M:%S" if has_time else "%Y-%m-%d")
    return out


def _column_order(dataset: GeneratedDataset, table: str, df: pd.DataFrame) -> list[str]:
    schema_table = dataset.schema.table(table)
    if schema_table is None:
        return list(df.columns)
    ordered = [c.name for c in schema_table.columns if c.name in df.columns]
    return ordered + [c for c in df.columns if c not in ordered]


def _invoice_ids(dataset: GeneratedDataset) -> list[str]:
    hints = dataset.schema.document_hints.invoice if dataset.schema.document_hints else None
    if hints is None:
        return []
    header = dataset.schema.table(hints.header_table)
    if header is None or hints.header_table not in dataset.tables:
        return []
    return dataset.tables[hints.header_table][header.primary_key].astype(str).head(MAX_INVOICE_PDFS).tolist()


def _readme(dataset: GeneratedDataset, invoice_count: int) -> str:
    counts = "\n".join(f"  {name}: {len(df):,} rows" for name, df in dataset.tables.items())
    lines = [
        f"DatDub synthetic dataset: {dataset.schema.name}",
        "",
        "Every value in this archive was generated. No row was copied from a real source.",
        "",
        "Tables:",
        counts,
        "",
        "Files:",
        "  tables/<table>.csv, tables/<table>.json  the generated rows",
        "  schema.json                              tables, columns, keys and business rules",
        "  validation_report.json                   checks run on the data (PASS / FAIL)",
        "  ground_truth.json                        records changed on purpose by edge cases",
    ]
    if invoice_count:
        lines.append(f"  documents/invoices/*.pdf                 the first {invoice_count} invoices as PDFs")
    return "\n".join(lines) + "\n"


def write_zip(dataset: GeneratedDataset, target: BinaryIO) -> None:
    """Write the export archive for `dataset` into the open binary file `target`."""
    invoice_ids = _invoice_ids(dataset)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for name, df in dataset.tables.items():
            frame = _formatted(df)[_column_order(dataset, name, df)]
            zf.writestr(f"tables/{name}.csv", frame.to_csv(index=False, lineterminator="\n"))
            zf.writestr(f"tables/{name}.json", frame.to_json(orient="records", indent=None))
        zf.writestr("schema.json", dataset.schema.model_dump_json(indent=2))
        zf.writestr("validation_report.json", dataset.report.model_dump_json(indent=2))
        zf.writestr(
            "ground_truth.json",
            json.dumps([g.model_dump(mode="json") for g in dataset.ground_truth], indent=2),
        )
        for invoice_id in invoice_ids:
            safe = "".join(ch for ch in invoice_id if ch.isalnum() or ch in "-_")[:60] or "invoice"
            zf.writestr(f"documents/invoices/{safe}.pdf", invoice_pdf_bytes(dataset, invoice_id))
        zf.writestr("README.txt", _readme(dataset, len(invoice_ids)))


def build_zip_file(dataset: GeneratedDataset) -> tempfile.SpooledTemporaryFile:
    """The archive in a spooled temp file, rewound and ready to stream. Caller closes it."""
    spool = tempfile.SpooledTemporaryFile(max_size=SPOOL_BYTES, mode="w+b")
    try:
        write_zip(dataset, spool)
        spool.seek(0)
    except Exception:
        spool.close()
        raise
    return spool


def zip_filename(dataset: GeneratedDataset) -> str:
    base = "".join(ch for ch in dataset.schema.name if ch.isalnum() or ch in "-_")[:60] or "dataset"
    return f"{base}.zip"
