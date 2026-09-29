"""Invoice documents. OWNER: Haider (H6).

Reads datasets only through `app.engine.store.get_dataset()`.
"""

from fastapi import APIRouter, Response

from app.core.exceptions import NotFound
from app.documents.invoice_pdf import invoice_pdf_bytes
from app.engine.store import get_dataset
from app.schemas import InvoiceListResponse

router = APIRouter(tags=["documents"])


@router.get("/datasets/{dataset_id}/documents/invoices", response_model=InvoiceListResponse)
def list_invoices(dataset_id: str) -> InvoiceListResponse:
    dataset = get_dataset(dataset_id)
    hints = dataset.schema.document_hints.invoice if dataset.schema.document_hints else None
    if hints is None:
        raise NotFound("This dataset has no invoice documents", code="no_documents")
    header = dataset.schema.table(hints.header_table)
    return InvoiceListResponse(invoice_ids=dataset.tables[hints.header_table][header.primary_key].astype(str).tolist())


@router.get(
    "/datasets/{dataset_id}/documents/invoices/{invoice_id}.pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def invoice_pdf(dataset_id: str, invoice_id: str) -> Response:
    """One synthetic invoice as a PDF. Sync route, so FastAPI runs it in a worker thread."""
    pdf = invoice_pdf_bytes(get_dataset(dataset_id), invoice_id)
    safe_name = "".join(ch for ch in invoice_id if ch.isalnum() or ch in "-_")[:60] or "invoice"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{safe_name}.pdf"', "Cache-Control": "no-store"},
    )
