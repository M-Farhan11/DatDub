"""Invoice documents. OWNER: Haider (H6).

F0 stub handed over by Farhan. Read datasets only through
`app.engine.store.get_dataset()`.
"""

from fastapi import APIRouter

from app.core.exceptions import AppError, NotFound
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


@router.get("/datasets/{dataset_id}/documents/invoices/{invoice_id}.pdf")
def invoice_pdf(dataset_id: str, invoice_id: str):
    get_dataset(dataset_id)
    raise AppError("Invoice PDF not implemented yet (H6)", code="not_implemented", status_code=501)
