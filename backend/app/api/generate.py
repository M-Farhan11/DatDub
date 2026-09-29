"""Generation endpoint."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.exceptions import RowsLimitExceeded
from app.engine import generator
from app.engine.store import GeneratedDataset, new_dataset_id, save_dataset
from app.schemas import GenerateRequest, GenerateResponse
from app.validation.checks import build_report

router = APIRouter(tags=["generate"])

PREVIEW_ROWS = 50


@router.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    cap = get_settings().row_cap
    too_big = {t: n for t, n in req.rows.items() if n > cap}
    if too_big:
        raise RowsLimitExceeded(f"Max {cap:,} rows per table. Requested: {too_big}")

    tables = generator.generate(req.schema_, req.rows, seed=req.seed)
    report = build_report(req.schema_, tables)
    dataset = GeneratedDataset(dataset_id=new_dataset_id(), schema=req.schema_, tables=tables, report=report)
    save_dataset(dataset)

    return GenerateResponse(
        dataset_id=dataset.dataset_id,
        row_counts={name: len(df) for name, df in tables.items()},
        previews={name: generator.to_records(df.head(PREVIEW_ROWS)) for name, df in tables.items()},
        report=report,
        ground_truth=dataset.ground_truth,
    )
