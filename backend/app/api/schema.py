"""Schema inference: prompt, CSV, Postgres, SQLite.

The routes stay thin; the work lives in `app.ingest` (CSV heuristics,
DB introspection behind `db_guard`, profiling, AI enrichment on metadata).
"""

from fastapi import APIRouter, File, Form, UploadFile

from app.ai.prompts import schema_draft_prompt
from app.ai.schemas import SchemaDraft
from app.ai.service import get_ai_service
from app.ai.validate import draft_to_schema
from app.core.config import get_settings
from app.ingest.csv import ingest_csv
from app.ingest.database import extract_postgres, extract_sqlite, list_tables
from app.schemas import (
    DbTablesRequest,
    DbTablesResponse,
    FromDbRequest,
    FromDbResponse,
    PromptSchemaRequest,
    SchemaResponse,
)
from app.schemas.api import ExtractMode

router = APIRouter(tags=["schema"])


@router.post("/schema/from-prompt", response_model=SchemaResponse)
async def from_prompt(req: PromptSchemaRequest) -> SchemaResponse:
    draft = await get_ai_service().generate_structured(schema_draft_prompt(req.prompt), SchemaDraft)
    schema, notes = draft_to_schema(draft, source="prompt")
    return SchemaResponse(schema=schema, notes=notes)


@router.post("/schema/from-csv", response_model=SchemaResponse)
async def from_csv(files: list[UploadFile] = File(...)) -> SchemaResponse:
    payload = [(f.filename or "table.csv", await f.read()) for f in files]
    schema, notes = await ingest_csv(payload)
    return SchemaResponse(schema=schema, notes=notes)


@router.post("/db/tables", response_model=DbTablesResponse)
def db_tables(req: DbTablesRequest) -> DbTablesResponse:
    return DbTablesResponse(tables=list_tables(req.connection))


@router.post("/schema/from-db", response_model=FromDbResponse)
async def from_db(req: FromDbRequest) -> FromDbResponse:
    return await extract_postgres(req.connection, req.tables, req.mode, _limit(req.sample_limit))


@router.post("/schema/from-sqlite", response_model=FromDbResponse)
async def from_sqlite(
    file: UploadFile = File(...),
    mode: ExtractMode = Form("schema_only"),
    sample_limit: int = Form(200, ge=1, le=1000),
    tables: str | None = Form(None, description="Comma-separated table names; all tables when empty"),
) -> FromDbResponse:
    selected = [t.strip() for t in (tables or "").split(",") if t.strip()]
    return await extract_sqlite(await file.read(), selected, mode, _limit(sample_limit))


def _limit(sample_limit: int) -> int:
    return max(1, min(sample_limit, get_settings().max_sample_limit))
