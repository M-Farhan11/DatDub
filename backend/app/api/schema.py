"""Schema inference: prompt, CSV, Postgres, SQLite.

F0 STUBS: responses are contract-valid fixtures so the frontend can
integrate. F3 replaces them with real inference.
"""

from fastapi import APIRouter, File, Form, UploadFile

from app.schemas import (
    DbTableInfo,
    DbTablesRequest,
    DbTablesResponse,
    FromDbRequest,
    FromDbResponse,
    PromptSchemaRequest,
    SchemaResponse,
)
from app.templates import get_template

router = APIRouter(tags=["schema"])

_STUB_NOTE = "Stub response (F0): real inference lands in F3."


@router.post("/schema/from-prompt", response_model=SchemaResponse)
def from_prompt(req: PromptSchemaRequest) -> SchemaResponse:
    schema = get_template("ecommerce").model_copy(update={"name": "prompt_schema", "source": "prompt"})
    return SchemaResponse(schema=schema, notes=[_STUB_NOTE])


@router.post("/schema/from-csv", response_model=SchemaResponse)
async def from_csv(files: list[UploadFile] = File(...)) -> SchemaResponse:
    schema = get_template("finance").model_copy(update={"name": "csv_schema", "source": "csv"})
    names = ", ".join(f.filename or "?" for f in files)
    return SchemaResponse(schema=schema, notes=[_STUB_NOTE, f"Received: {names}"])


@router.post("/db/tables", response_model=DbTablesResponse)
def db_tables(req: DbTablesRequest) -> DbTablesResponse:
    return DbTablesResponse(
        tables=[
            DbTableInfo(name="customers", column_count=9, estimated_rows=300, references=[]),
            DbTableInfo(name="invoices", column_count=7, estimated_rows=900, references=["customers"]),
            DbTableInfo(name="invoice_items", column_count=5, estimated_rows=2700, references=["invoices"]),
            DbTableInfo(name="payments", column_count=5, estimated_rows=800, references=["invoices"]),
        ]
    )


def _stub_from_db(tables: list[str], mode: str, sample_limit: int, source: str) -> FromDbResponse:
    schema = get_template("finance").model_copy(update={"name": f"{source}_schema", "source": source})
    wanted = set(tables)
    # auto-add FK parents
    auto_added: list[str] = []
    changed = True
    while changed:
        changed = False
        for t in schema.tables:
            if t.name in wanted:
                for fk in t.foreign_keys:
                    if fk.ref_table not in wanted:
                        wanted.add(fk.ref_table)
                        auto_added.append(fk.ref_table)
                        changed = True
    schema.tables = [t for t in schema.tables if t.name in wanted]
    schema.rules = [
        r
        for r in schema.rules
        if r.table in wanted and all(v in wanted for k, v in r.params.items() if k.endswith("table"))
    ]
    if schema.document_hints and schema.document_hints.invoice:
        hints = schema.document_hints.invoice
        if not {hints.header_table, hints.items_table, hints.party_table} <= wanted:
            schema.document_hints = None
    rows_sampled = sample_limit * len(schema.tables) if mode == "schema_and_sample" else 0
    return FromDbResponse(schema=schema, auto_added=auto_added, rows_sampled=rows_sampled, notes=[_STUB_NOTE])


@router.post("/schema/from-db", response_model=FromDbResponse)
def from_db(req: FromDbRequest) -> FromDbResponse:
    return _stub_from_db(req.tables, req.mode, req.sample_limit, "postgres")


@router.post("/schema/from-sqlite", response_model=FromDbResponse)
async def from_sqlite(
    file: UploadFile = File(...),
    mode: str = Form("schema_only"),
    sample_limit: int = Form(200),
    tables: str | None = Form(None, description="Comma-separated table names; all tables when empty"),
) -> FromDbResponse:
    selected = [t.strip() for t in (tables or "").split(",") if t.strip()] or [
        "customers",
        "invoices",
        "invoice_items",
        "payments",
    ]
    return _stub_from_db(selected, mode, min(max(sample_limit, 1), 1000), "sqlite")
