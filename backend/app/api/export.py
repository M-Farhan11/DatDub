"""ZIP export. OWNER: Haider (H7).

Reads datasets only through `app.engine.store.get_dataset()`.
"""

import os
from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from app.engine.store import get_dataset
from app.export.zip_export import build_zip_file, zip_filename

router = APIRouter(tags=["export"])

CHUNK = 1024 * 1024


@router.get(
    "/datasets/{dataset_id}/export.zip",
    response_class=StreamingResponse,
    responses={200: {"content": {"application/zip": {}}}},
)
def export_zip(dataset_id: str) -> StreamingResponse:
    """Whole dataset as a ZIP. Sync route: the archive is built in a worker thread."""
    dataset = get_dataset(dataset_id)
    spool = build_zip_file(dataset)
    size = spool.seek(0, os.SEEK_END)
    spool.seek(0)

    def chunks() -> Iterator[bytes]:
        while block := spool.read(CHUNK):
            yield block

    return StreamingResponse(
        chunks(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename(dataset)}"',
            "Content-Length": str(size),
            "Cache-Control": "no-store",
        },
        background=BackgroundTask(spool.close),
    )
