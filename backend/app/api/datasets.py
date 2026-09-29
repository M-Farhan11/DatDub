"""Paged reads of generated tables."""

from fastapi import APIRouter, Query

from app.core.exceptions import NotFound
from app.engine.generator import to_records
from app.engine.store import get_dataset
from app.schemas import TablePage

router = APIRouter(tags=["datasets"])


@router.get("/datasets/{dataset_id}/tables/{table}", response_model=TablePage)
def table_page(
    dataset_id: str,
    table: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
) -> TablePage:
    dataset = get_dataset(dataset_id)
    df = dataset.tables.get(table)
    if df is None:
        raise NotFound(f"Table '{table}' not in dataset", code="table_not_found")
    return TablePage(table=table, total=len(df), rows=to_records(df.iloc[offset : offset + limit]))
