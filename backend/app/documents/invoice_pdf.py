"""Invoice PDF rendering with ReportLab. OWNER: Haider (H6).

Layout follows the invoice in the theme PDF: "INVOICE" + number, Billed to /
From, an Item / Qty / Price / Amount table and a highlighted total. Every
value comes from the generated data (see `invoice_data.py`); the only fixed
text is the synthetic supplier and the "not a real invoice" footer.
"""

from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.engine.store import GeneratedDataset

from .invoice_data import InvoiceData, extract_invoice

INK = colors.HexColor("#16213A")
MUTED = colors.HexColor("#5B6475")
ACCENT = colors.HexColor("#157A6E")
RULE = colors.HexColor("#D5D9E0")
HEADER_BG = colors.HexColor("#EEF0F3")

SUPPLIER = ["DatDub Test Supplier Ltd.", "Synthetic sample data"]
SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "INR": "₹"}

_base = ParagraphStyle("base", fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK)
_muted = ParagraphStyle("muted", parent=_base, textColor=MUTED)
_label = ParagraphStyle("label", parent=_base, fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=ACCENT)
_title = ParagraphStyle("title", parent=_base, fontName="Helvetica-Bold", fontSize=20, leading=24)
_number = ParagraphStyle("number", parent=_muted, fontSize=11, alignment=TA_RIGHT)
_right = ParagraphStyle("right", parent=_base, alignment=TA_RIGHT)
_right_label = ParagraphStyle("rightlabel", parent=_label, alignment=TA_RIGHT)
_total = ParagraphStyle("total", parent=_base, fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=ACCENT, alignment=TA_RIGHT)
_footer = ParagraphStyle("footer", parent=_muted, fontSize=7.5, leading=10)


def money(value: float | None, currency: str) -> str:
    if value is None:
        return "—"
    sign = "-" if value < 0 else ""
    symbol = SYMBOLS.get(currency.upper())
    amount = f"{abs(value):,.2f}"
    return f"{sign}{symbol}{amount}" if symbol else f"{sign}{amount} {currency.upper()}"


def _qty(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def _p(text: str, style: ParagraphStyle = _base) -> Paragraph:
    return Paragraph(escape(text), style)


def render_invoice_pdf(data: InvoiceData, *, compress: bool = True) -> bytes:
    """PDF bytes for one invoice. Deterministic: the same data gives the same bytes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Invoice {data.invoice_id}",
        author="DatDub (synthetic data)",
        subject=f"Synthetic invoice from dataset {data.dataset_name}",
        invariant=1,
        pageCompression=1 if compress else 0,
    )
    width = doc.width
    cur = data.currency
    story: list = []

    head = Table([[_p("INVOICE", _title), _p(f"#{data.invoice_id}", _number)]], colWidths=[width * 0.6, width * 0.4])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story += [head, Spacer(1, 3 * mm), HRFlowable(width="100%", thickness=0.8, color=RULE), Spacer(1, 5 * mm)]

    billed = [_p("BILLED TO", _label)] + [_p(line) for line in (data.billed_to or ["—"])]
    supplier = [_p("FROM", _right_label)] + [_p(line, _right) for line in SUPPLIER]
    parties = Table([[billed, supplier]], colWidths=[width * 0.6, width * 0.4])
    parties.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story += [parties, Spacer(1, 5 * mm)]

    meta = [(label, value) for label, value in (("ISSUE DATE", data.issue_date), ("DUE DATE", data.due_date), ("STATUS", data.status)) if value]
    if meta:
        cells = [[_p(label, _label) for label, _ in meta], [_p(value) for _, value in meta]]
        meta_table = Table(cells, colWidths=[width / len(meta)] * len(meta), hAlign="LEFT")
        meta_table.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
        story += [meta_table, Spacer(1, 6 * mm)]

    rows = [[_p("Item", ParagraphStyle("th", parent=_base, fontName="Helvetica-Bold")),
             _p("Qty", ParagraphStyle("thr", parent=_right, fontName="Helvetica-Bold")),
             _p("Price", ParagraphStyle("thr2", parent=_right, fontName="Helvetica-Bold")),
             _p("Amount", ParagraphStyle("thr3", parent=_right, fontName="Helvetica-Bold"))]]
    for item in data.items:
        rows.append([_p(item.description), _p(_qty(item.quantity), _right), _p(money(item.unit_price, cur) if item.unit_price is not None else "", _right), _p(money(item.amount, cur), _right)])
    if not data.items:
        rows.append([_p("No line items", _muted), "", "", ""])
    items = Table(rows, colWidths=[width * 0.52, width * 0.12, width * 0.18, width * 0.18], repeatRows=1)
    items.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("GRID", (0, 0), (-1, -1), 0.6, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story += [items, Spacer(1, 5 * mm)]

    totals: list[list] = []
    show_subtotal = data.tax is not None or data.total is None or abs(data.subtotal - (data.total or 0)) >= 0.005
    if show_subtotal:
        totals.append([_p("Subtotal", _right), _p(money(data.subtotal, cur), _right)])
    if data.tax is not None:
        totals.append([_p("Tax", _right), _p(money(data.tax, cur), _right)])
    total = data.total if data.total is not None else data.subtotal
    totals.append([_p("", _right), _p(f"Total: {money(total, cur)}", _total)])
    if data.paid is not None:
        totals.append([_p("Amount paid", _right), _p(money(data.paid, cur), _right)])
        totals.append([_p("Balance due", _right), _p(money(round(total - data.paid, 2), cur), _right)])
    totals_table = Table(totals, colWidths=[width * 0.6, width * 0.4])
    totals_table.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    story += [totals_table, Spacer(1, 12 * mm), HRFlowable(width="100%", thickness=0.5, color=RULE), Spacer(1, 2 * mm)]
    story.append(
        _p(f"Synthetic document generated by DatDub from dataset {data.dataset_name}. Not a real invoice.", _footer)
    )

    doc.build(story)
    return buf.getvalue()


def invoice_pdf_bytes(dataset: GeneratedDataset, invoice_id: str, *, compress: bool = True) -> bytes:
    """Render one invoice of a stored dataset (also used by the ZIP export)."""
    return render_invoice_pdf(extract_invoice(dataset, invoice_id), compress=compress)
