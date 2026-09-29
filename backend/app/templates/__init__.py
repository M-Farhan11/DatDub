"""Built-in dataset templates (no AI involved)."""

from collections.abc import Callable

from app.schemas import DatasetSchema, TemplateSummary
from app.templates import ecommerce, finance

_TEMPLATES: dict[str, tuple[str, str, Callable[[], DatasetSchema]]] = {
    "finance": ("Finance", "Customers, invoices, line items and payments. Includes invoice PDFs.", finance.build),
    "ecommerce": ("E-commerce", "Customers, orders, order items and payments.", ecommerce.build),
}


def list_templates() -> list[TemplateSummary]:
    return [
        TemplateSummary(id=tid, name=name, description=desc, tables=len(build().tables))
        for tid, (name, desc, build) in _TEMPLATES.items()
    ]


def get_template(template_id: str) -> DatasetSchema | None:
    entry = _TEMPLATES.get(template_id)
    return entry[2]() if entry else None
