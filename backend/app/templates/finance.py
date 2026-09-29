"""Finance template: customers → invoices → invoice_items, invoices → payments."""

from app.schemas import ColumnSchema as C
from app.schemas import DatasetSchema, DocumentHints, ForeignKey, InvoiceHints, Rule, TableSchema

INVOICE_STATUSES = ["draft", "sent", "paid", "overdue", "void"]
PAYMENT_METHODS = ["card", "bank_transfer", "cash", "paypal"]


def build() -> DatasetSchema:
    customers = TableSchema(
        name="customers",
        primary_key="customer_id",
        row_count_hint=200,
        columns=[
            C(name="customer_id", data_type="string", semantic_type="id", unique=True),
            C(name="full_name", data_type="string", semantic_type="person_name", pii=True),
            C(name="email", data_type="string", semantic_type="email", unique=True, pii=True),
            C(name="phone", data_type="string", semantic_type="phone", nullable=True, pii=True),
            C(name="company", data_type="string", semantic_type="company", nullable=True),
            C(name="address", data_type="string", semantic_type="address", pii=True),
            C(name="city", data_type="string", semantic_type="city"),
            C(name="country", data_type="string", semantic_type="country"),
            C(name="created_at", data_type="date", semantic_type="date", min="2023-01-01", max="2025-12-31"),
        ],
    )
    invoices = TableSchema(
        name="invoices",
        primary_key="invoice_id",
        columns=[
            C(name="invoice_id", data_type="string", semantic_type="id", unique=True),
            C(name="customer_id", data_type="string", semantic_type="id"),
            C(name="issue_date", data_type="date", semantic_type="date"),
            C(name="due_date", data_type="date", semantic_type="date"),
            C(name="status", data_type="string", semantic_type="status", allowed_values=INVOICE_STATUSES),
            C(name="currency", data_type="string", semantic_type="category", allowed_values=["USD"]),
            C(name="total", data_type="decimal", semantic_type="currency_amount", min=0),
        ],
        foreign_keys=[
            ForeignKey(column="customer_id", ref_table="customers", ref_column="customer_id", min_children=1, max_children=8)
        ],
    )
    invoice_items = TableSchema(
        name="invoice_items",
        primary_key="item_id",
        columns=[
            C(name="item_id", data_type="string", semantic_type="id", unique=True),
            C(name="invoice_id", data_type="string", semantic_type="id"),
            C(name="description", data_type="string", semantic_type="text"),
            C(name="quantity", data_type="integer", semantic_type="quantity", min=1, max=20),
            C(name="unit_price", data_type="decimal", semantic_type="currency_amount", min=5, max=2000),
        ],
        foreign_keys=[
            ForeignKey(column="invoice_id", ref_table="invoices", ref_column="invoice_id", min_children=1, max_children=6)
        ],
    )
    payments = TableSchema(
        name="payments",
        primary_key="payment_id",
        columns=[
            C(name="payment_id", data_type="string", semantic_type="id", unique=True),
            C(name="invoice_id", data_type="string", semantic_type="id"),
            C(name="amount", data_type="decimal", semantic_type="currency_amount", min=0),
            C(name="method", data_type="string", semantic_type="category", allowed_values=PAYMENT_METHODS),
            C(name="paid_at", data_type="date", semantic_type="date"),
        ],
        foreign_keys=[
            ForeignKey(column="invoice_id", ref_table="invoices", ref_column="invoice_id", min_children=0, max_children=2)
        ],
    )
    rules = [
        Rule(
            id="r1",
            kind="sum_of_children",
            table="invoices",
            column="total",
            params={"child_table": "invoice_items", "expr": "quantity * unit_price"},
            description="Invoice total equals the sum of its line items",
        ),
        Rule(
            id="r2",
            kind="date_order",
            table="invoices",
            column="due_date",
            params={"before": "issue_date", "after": "due_date"},
            description="Invoice issue date is on or before its due date",
        ),
        Rule(
            id="r3",
            kind="lte_parent",
            table="payments",
            column="amount",
            params={"parent_table": "invoices", "parent_column": "total"},
            description="A payment never exceeds its invoice total",
        ),
        Rule(
            id="r4",
            kind="date_order",
            table="payments",
            column="paid_at",
            params={"before": "issue_date", "after": "paid_at", "via_fk": "invoice_id"},
            description="A payment is made on or after the invoice issue date",
        ),
        Rule(
            id="r5",
            kind="date_order",
            table="invoices",
            column="issue_date",
            params={"before": "created_at", "after": "issue_date", "via_fk": "customer_id"},
            description="An invoice is issued on or after the customer was created",
        ),
        Rule(
            id="r6",
            kind="allowed_values",
            table="invoices",
            column="status",
            params={"values": INVOICE_STATUSES},
            description="Invoice status is one of the known statuses",
        ),
        Rule(
            id="r7",
            kind="range",
            table="invoice_items",
            column="quantity",
            params={"min": 1, "max": 20},
            description="Line item quantity is between 1 and 20",
        ),
    ]
    return DatasetSchema(
        name="finance_demo",
        source="template",
        tables=[customers, invoices, invoice_items, payments],
        rules=rules,
        document_hints=DocumentHints(
            invoice=InvoiceHints(header_table="invoices", items_table="invoice_items", party_table="customers")
        ),
    )
