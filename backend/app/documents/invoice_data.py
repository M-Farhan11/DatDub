"""Collect one invoice's data from a generated dataset. OWNER: Haider (H6).

Columns are found through the schema, not hard-coded names:
- `document_hints.invoice` names the header / items / party tables;
- the `sum_of_children` rule on the header gives the total column and the
  line-amount expression (e.g. ``quantity * unit_price``);
- semantic types fill in the rest (dates, status, names, addresses).

Reads datasets only through the `GeneratedDataset` returned by
`app.engine.store.get_dataset()`.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

from app.core.exceptions import NotFound
from app.engine.store import GeneratedDataset
from app.schemas import ColumnSchema, DatasetSchema, TableSchema


@dataclass
class LineItem:
    description: str
    quantity: float
    unit_price: float | None
    amount: float


@dataclass
class InvoiceData:
    invoice_id: str
    dataset_name: str
    currency: str
    issue_date: str | None = None
    due_date: str | None = None
    status: str | None = None
    billed_to: list[str] = field(default_factory=list)
    items: list[LineItem] = field(default_factory=list)
    tax: float | None = None
    total: float | None = None
    paid: float | None = None

    @property
    def subtotal(self) -> float:
        return round(sum(i.amount for i in self.items), 2)


def _hints(schema: DatasetSchema):
    hints = schema.document_hints.invoice if schema.document_hints else None
    if hints is None:
        raise NotFound("This dataset has no invoice documents", code="no_documents")
    header, items, party = (schema.table(hints.header_table), schema.table(hints.items_table), schema.table(hints.party_table))
    if header is None or items is None:
        raise NotFound("This dataset has no invoice documents", code="no_documents")
    return header, items, party


def _first(table: TableSchema, *semantic: str, exclude: set[str] | None = None) -> ColumnSchema | None:
    exclude = exclude or set()
    for kind in semantic:
        for col in table.columns:
            if col.semantic_type == kind and col.name not in exclude:
                return col
    return None


def _named(table: TableSchema, *needles: str) -> ColumnSchema | None:
    for col in table.columns:
        if any(n in col.name.lower() for n in needles):
            return col
    return None


def _num(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _text(value) -> str | None:
    """Printable text for a cell: None for missing values, dates as YYYY-MM-DD."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    return s or None


def _line_columns(schema: DatasetSchema, header: TableSchema, items: TableSchema):
    """(total column, quantity column, price column) using the sum_of_children rule when present."""
    rule = next(
        (
            r
            for r in schema.rules
            if r.kind == "sum_of_children" and r.table == header.name and r.params.get("child_table") == items.name
        ),
        None,
    )
    total_col = rule.column if rule else (_first(header, "currency_amount").name if _first(header, "currency_amount") else None)
    qty_col = price_col = None
    if rule:
        factors = [f.strip() for f in re.split(r"\*", str(rule.params.get("expr", ""))) if f.strip()]
        names = {c.name for c in items.columns}
        factors = [f for f in factors if f in names]
        if len(factors) == 2:
            by_name = {c.name: c for c in items.columns}
            a, b = factors
            qty_col, price_col = (a, b) if by_name[a].semantic_type == "quantity" or by_name[b].semantic_type == "currency_amount" else (b, a)
        elif len(factors) == 1:
            price_col = factors[0]  # amount per line is the column itself
            q = _first(items, "quantity")
            qty_col = q.name if q else None
            return total_col, qty_col, price_col, True
    if price_col is None:
        p = _first(items, "currency_amount")
        price_col = p.name if p else None
    if qty_col is None:
        q = _first(items, "quantity")
        qty_col = q.name if q else None
    return total_col, qty_col, price_col, False


def extract_invoice(dataset: GeneratedDataset, invoice_id: str) -> InvoiceData:
    schema = dataset.schema
    header, items, party = _hints(schema)
    header_df = dataset.tables[header.name]
    match = header_df[header_df[header.primary_key].astype(str) == invoice_id]
    if match.empty:
        raise NotFound(f"Invoice '{invoice_id[:40]}' is not in this dataset", code="invoice_not_found")
    inv = match.iloc[0]

    total_col, qty_col, price_col, price_is_amount = _line_columns(schema, header, items)
    currency_col = _named(header, "currency")
    date_cols = [c for c in header.columns if c.semantic_type in ("date", "datetime")]
    issue_col = _named(header, "issue", "invoice_date", "created") or (date_cols[0] if date_cols else None)
    due_col = _named(header, "due") or (date_cols[1] if len(date_cols) > 1 else None)
    status_col = _first(header, "status")
    tax_col = _named(header, "tax", "vat")

    data = InvoiceData(
        invoice_id=invoice_id,
        dataset_name=schema.name,
        currency=(_text(inv[currency_col.name]) if currency_col else None) or "USD",
        issue_date=_text(inv[issue_col.name]) if issue_col else None,
        due_date=_text(inv[due_col.name]) if due_col and due_col is not issue_col else None,
        status=_text(inv[status_col.name]) if status_col else None,
        tax=_num(inv[tax_col.name]) if tax_col and tax_col.name != total_col else None,
        total=_num(inv[total_col]) if total_col else None,
    )

    # line items
    fk = next((f for f in items.foreign_keys if f.ref_table == header.name), None)
    if fk is not None:
        items_df = dataset.tables[items.name]
        lines = items_df[items_df[fk.column].astype(str) == invoice_id]
        desc_col = _first(items, "text", "sku", "generic_string", "category", "status", exclude={fk.column})
        for _, row in lines.iterrows():
            qty = _num(row[qty_col]) if qty_col else 1.0
            price = _num(row[price_col]) if price_col else None
            qty = 1.0 if qty is None else qty
            amount = (price or 0.0) if price_is_amount else (qty * (price or 0.0))
            data.items.append(
                LineItem(
                    description=(_text(row[desc_col.name]) if desc_col else None) or str(row[items.primary_key]),
                    quantity=qty,
                    unit_price=None if price_is_amount else price,
                    amount=round(amount, 2),
                )
            )

    # billed-to party
    party_fk = next((f for f in header.foreign_keys if party and f.ref_table == party.name), None)
    if party is not None and party_fk is not None:
        party_df = dataset.tables[party.name]
        who = party_df[party_df[party.primary_key].astype(str) == str(inv[party_fk.column])]
        if not who.empty:
            p = who.iloc[0]
            lines_out: list[str] = []
            for kinds in (("company",), ("person_name",), ("first_name",), ("address",)):
                col = _first(party, *kinds)
                val = _text(p[col.name]) if col else None
                if val and val not in lines_out:
                    lines_out.append(val)
            if not any(_first(party, k) for k in ("person_name", "company")):
                first, last = _first(party, "first_name"), _first(party, "last_name")
                if first and last:
                    lines_out.insert(0, f"{_text(p[first.name]) or ''} {_text(p[last.name]) or ''}".strip())
            place = ", ".join(v for v in (_text(p[c.name]) for c in (_first(party, "city"), _first(party, "country")) if c) if v)
            if place:
                lines_out.append(place)
            email = _first(party, "email")
            if email and _text(p[email.name]):
                lines_out.append(_text(p[email.name]) or "")
            data.billed_to = lines_out

    # payments: a table whose lte_parent rule points at the invoice total
    pay_rule = next(
        (r for r in schema.rules if r.kind == "lte_parent" and r.params.get("parent_table") == header.name),
        None,
    )
    pay_table = schema.table(pay_rule.table) if pay_rule else None
    pay_fk = next((f for f in pay_table.foreign_keys if f.ref_table == header.name), None) if pay_table else None
    if pay_rule and pay_table and pay_fk:
        pay_df = dataset.tables[pay_table.name]
        amounts = pd.to_numeric(pay_df.loc[pay_df[pay_fk.column].astype(str) == invoice_id, pay_rule.column], errors="coerce")
        data.paid = round(float(amounts.fillna(0).sum()), 2)

    return data
