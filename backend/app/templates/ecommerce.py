"""E-commerce template: customers → orders → order_items, orders → payments."""

from app.schemas import ColumnSchema as C
from app.schemas import DatasetSchema, ForeignKey, Rule, TableSchema

ORDER_STATUSES = ["pending", "paid", "shipped", "delivered", "cancelled", "refunded"]
PAYMENT_METHODS = ["card", "paypal", "apple_pay", "bank_transfer"]


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
            C(name="city", data_type="string", semantic_type="city"),
            C(name="country", data_type="string", semantic_type="country"),
            C(name="created_at", data_type="date", semantic_type="date", min="2023-01-01", max="2025-12-31"),
        ],
    )
    orders = TableSchema(
        name="orders",
        primary_key="order_id",
        columns=[
            C(name="order_id", data_type="string", semantic_type="id", unique=True),
            C(name="customer_id", data_type="string", semantic_type="id"),
            C(name="order_date", data_type="date", semantic_type="date"),
            C(name="status", data_type="string", semantic_type="status", allowed_values=ORDER_STATUSES),
            C(name="total", data_type="decimal", semantic_type="currency_amount", min=0),
        ],
        foreign_keys=[
            ForeignKey(column="customer_id", ref_table="customers", ref_column="customer_id", min_children=0, max_children=10)
        ],
    )
    order_items = TableSchema(
        name="order_items",
        primary_key="item_id",
        columns=[
            C(name="item_id", data_type="string", semantic_type="id", unique=True),
            C(name="order_id", data_type="string", semantic_type="id"),
            C(name="sku", data_type="string", semantic_type="sku"),
            C(name="quantity", data_type="integer", semantic_type="quantity", min=1, max=10),
            C(name="unit_price", data_type="decimal", semantic_type="currency_amount", min=1, max=500),
        ],
        foreign_keys=[
            ForeignKey(column="order_id", ref_table="orders", ref_column="order_id", min_children=1, max_children=5)
        ],
    )
    payments = TableSchema(
        name="payments",
        primary_key="payment_id",
        columns=[
            C(name="payment_id", data_type="string", semantic_type="id", unique=True),
            C(name="order_id", data_type="string", semantic_type="id"),
            C(name="amount", data_type="decimal", semantic_type="currency_amount", min=0),
            C(name="method", data_type="string", semantic_type="category", allowed_values=PAYMENT_METHODS),
            C(name="paid_at", data_type="date", semantic_type="date"),
        ],
        foreign_keys=[
            ForeignKey(column="order_id", ref_table="orders", ref_column="order_id", cardinality="1:1", min_children=0, max_children=1)
        ],
    )
    rules = [
        Rule(
            id="r1",
            kind="sum_of_children",
            table="orders",
            column="total",
            params={"child_table": "order_items", "expr": "quantity * unit_price"},
            description="Order total equals the sum of its items",
        ),
        Rule(
            id="r2",
            kind="date_order",
            table="orders",
            column="order_date",
            params={"before": "created_at", "after": "order_date", "via_fk": "customer_id"},
            description="An order is placed on or after the customer signed up",
        ),
        Rule(
            id="r3",
            kind="date_order",
            table="payments",
            column="paid_at",
            params={"before": "order_date", "after": "paid_at", "via_fk": "order_id"},
            description="A payment is made on or after the order date",
        ),
        Rule(
            id="r4",
            kind="lte_parent",
            table="payments",
            column="amount",
            params={"parent_table": "orders", "parent_column": "total"},
            description="A payment never exceeds its order total",
        ),
        Rule(
            id="r5",
            kind="allowed_values",
            table="orders",
            column="status",
            params={"values": ORDER_STATUSES},
            description="Order status is one of the known statuses",
        ),
    ]
    return DatasetSchema(name="ecommerce_demo", source="template", tables=[customers, orders, order_items, payments], rules=rules)
