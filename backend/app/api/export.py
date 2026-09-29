"""ZIP export. OWNER: Haider (H7).

F0 stub handed over by Farhan. Read datasets only through
`app.engine.store.get_dataset()`.
"""

from fastapi import APIRouter

from app.core.exceptions import AppError
from app.engine.store import get_dataset

router = APIRouter(tags=["export"])


@router.get("/datasets/{dataset_id}/export.zip")
def export_zip(dataset_id: str):
    get_dataset(dataset_id)
    raise AppError("ZIP export not implemented yet (H7)", code="not_implemented", status_code=501)
