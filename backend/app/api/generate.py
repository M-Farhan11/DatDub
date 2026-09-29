"""Generation endpoint: check → generate → inject scenarios → validate → store."""

import threading

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.exceptions import ServerBusy
from app.engine import generator
from app.engine.scenarios import inject
from app.engine.store import GeneratedDataset, new_dataset_id, save_dataset
from app.schemas import GenerateRequest, GenerateResponse
from app.validation.checks import build_report
from app.validation.schema_check import check_generate_request

router = APIRouter(tags=["generate"])

PREVIEW_ROWS = 50
BUSY_WAIT_SECONDS = 30

_slots: threading.BoundedSemaphore | None = None
_slots_lock = threading.Lock()


def _generation_slots() -> threading.BoundedSemaphore:
    global _slots
    with _slots_lock:
        if _slots is None:
            _slots = threading.BoundedSemaphore(max(1, get_settings().max_concurrent_generations))
        return _slots


@router.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    settings = get_settings()
    check_generate_request(req, settings.row_cap, settings.max_total_cells)

    slots = _generation_slots()
    if not slots.acquire(timeout=BUSY_WAIT_SECONDS):
        raise ServerBusy("The server is busy with other generations. Try again in a moment.")
    try:
        tables = generator.generate(
            req.schema_,
            req.rows,
            seed=req.seed,
            null_rate=req.null_rate,
            outlier_rate=req.outlier_rate,
            locale=req.locale,
            row_cap=settings.row_cap,
        )
        ground_truth, expected = inject(req.schema_, tables, req.scenarios, req.seed)
        report = build_report(req.schema_, tables, ground_truth, expected)
    finally:
        slots.release()

    dataset = GeneratedDataset(
        dataset_id=new_dataset_id(), schema=req.schema_, tables=tables, report=report, ground_truth=ground_truth
    )
    save_dataset(dataset)

    return GenerateResponse(
        dataset_id=dataset.dataset_id,
        row_counts={name: len(df) for name, df in tables.items()},
        previews={name: generator.to_records(df.head(PREVIEW_ROWS)) for name, df in tables.items()},
        report=report,
        ground_truth=ground_truth,
    )
