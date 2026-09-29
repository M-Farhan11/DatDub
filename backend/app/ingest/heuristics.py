"""Column type and semantic heuristics, used before (and without) AI.

`infer_column` looks at a column name plus its sample values (pandas
Series, possibly all strings from a CSV) and returns a data type, a
semantic type, a PII flag and a confidence. Value-regex matches are
treated as strong evidence (confidence >= 0.9) so AI enrichment does not
override them.
"""

import re
from dataclasses import dataclass

import pandas as pd

from app.schemas.dataset import DataType, SemanticType

CATEGORY_MAX_DISTINCT = 20  # also the privacy threshold for sending category values to AI
STRONG = 0.9  # heuristic confidence at or above which AI does not override

_EMAIL = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
_PHONE = re.compile(r"^\+?[\d\s().-]{7,20}$")
_URL = re.compile(r"^https?://\S+$", re.I)
_IBAN = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$")
_CURRENCY = re.compile(r"^\s*-?[$€£¥₹]\s?-?[\d,]+(\.\d+)?\s*$|^\s*-?[\d,]+(\.\d+)?\s?(USD|EUR|GBP|PKR)\s*$", re.I)
_BOOL = {"true", "false", "yes", "no", "t", "f", "y", "n"}
BOOL_TRUE = {"true", "yes", "y", "t", "1", "1.0"}
BOOL_FALSE = {"false", "no", "n", "f", "0", "0.0"}


def bool_label(value) -> str | None:
    """"true" / "false" for any boolean spelling (yes/no, t/f, 1/0, True/False), else None."""
    v = str(value).strip().lower()
    return "true" if v in BOOL_TRUE else "false" if v in BOOL_FALSE else None
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")

# (name pattern, semantic type, pii)
_NAME_RULES: list[tuple[str, SemanticType, bool]] = [
    (r"e_?mail", "email", True),
    (r"phone|mobile|tel$|telephone", "phone", True),
    (r"first_?name|given_?name", "first_name", True),
    (r"last_?name|surname|family_?name", "last_name", True),
    (r"^(full_?)?name$|customer_?name|contact_?name|person", "person_name", True),
    (r"iban|account_?(no|number)", "iban", True),
    (r"address|street", "address", True),
    (r"city|town", "city", False),
    (r"country", "country", False),
    (r"company|organi[sz]ation|employer|vendor|supplier", "company", False),
    (r"url|website|link", "url", False),
    (r"sku|product_?code", "sku", False),
    (r"status|state$", "status", False),
    (r"type$|category|method|segment|currency|channel|tier", "category", False),
    (r"amount|price|total|cost|balance|revenue|salary|fee|tax|subtotal", "currency_amount", False),
    (r"qty|quantity|units", "quantity", False),
    (r"pct|percent|ratio|rate$", "percentage", False),
    (r"description|notes?$|comment|memo", "text", False),
]

_PII_SEMANTICS = {"person_name", "first_name", "last_name", "email", "phone", "address", "iban"}


@dataclass
class ColumnGuess:
    data_type: DataType
    semantic_type: SemanticType
    pii: bool
    confidence: float
    # set when a CSV string column had to be cleaned to parse (currency symbols, commas)
    parsed: pd.Series | None = None


def is_id_name(name: str) -> bool:
    """`id`, `customer_id`, `customer-id` or camelCase `customerId`."""
    n = name.lower()
    return n == "id" or n.endswith(("_id", "-id")) or (len(name) > 2 and name.endswith("Id"))


def name_semantics(name: str) -> tuple[SemanticType, bool] | None:
    n = name.lower()
    if is_id_name(name):
        return "id", False
    for pattern, semantic, pii in _NAME_RULES:
        if re.search(pattern, n):
            return semantic, pii
    return None


def is_pii_semantic(semantic: str) -> bool:
    return semantic in _PII_SEMANTICS


def infer_data_type(values: pd.Series) -> tuple[DataType, pd.Series | None]:
    """Infer the data type of a column. `values` has nulls already dropped.

    Returns the type and, when the raw values were strings that needed
    parsing, the parsed Series (numbers or datetimes) for profiling.
    """
    if values.empty:
        return "string", None
    if pd.api.types.is_bool_dtype(values):
        return "boolean", None
    if pd.api.types.is_integer_dtype(values):
        return "integer", None
    if pd.api.types.is_float_dtype(values):
        return ("integer" if (values % 1 == 0).all() else "float"), None
    if pd.api.types.is_datetime64_any_dtype(values):
        return ("date" if (values.dt.normalize() == values).all() else "datetime"), None

    text = values.astype(str).str.strip()
    lowered = text.str.lower()
    if lowered.isin(_BOOL).all() and lowered.nunique() <= 2:
        return "boolean", lowered.isin({"true", "yes", "t", "y"})

    numeric = pd.to_numeric(text, errors="coerce")
    if numeric.notna().all():
        # leading zeros ("00123") are codes, not numbers
        if text.str.match(r"^0\d").any():
            return "string", None
        if (numeric % 1 == 0).all() and not text.str.contains(r"[.eE]").any():
            return "integer", numeric
        decimals = text.str.extract(r"\.(\d+)$")[0].dropna().str.len()
        return ("decimal" if not decimals.empty and decimals.max() <= 2 else "float"), numeric

    if text.str.match(_CURRENCY).mean() >= 0.9:
        cleaned = pd.to_numeric(text.str.replace(r"[^\d.-]", "", regex=True), errors="coerce")
        if cleaned.notna().mean() >= 0.9:
            return "decimal", cleaned

    if text.str.match(_ISO_DATE).mean() >= 0.9 or text.str.match(r"^\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}").mean() >= 0.9:
        parsed = pd.to_datetime(text, errors="coerce", format="mixed")
        if parsed.notna().mean() >= 0.9:
            has_time = (parsed.dropna().dt.normalize() != parsed.dropna()).any()
            return ("datetime" if has_time else "date"), parsed

    return "string", None


def infer_column(name: str, values: pd.Series) -> ColumnGuess:
    """Guess type + semantics from a column name and its non-null sample values."""
    data_type, parsed = infer_data_type(values)
    by_name = name_semantics(name)

    if data_type == "string" and not values.empty:
        text = values.astype(str).str.strip()
        for regex, semantic in ((_EMAIL, "email"), (_URL, "url"), (_IBAN, "iban")):
            if text.str.match(regex).mean() >= 0.9:
                return ColumnGuess("string", semantic, is_pii_semantic(semantic), 0.95)
        digits = text.str.count(r"\d")
        if text.str.match(_PHONE).mean() >= 0.9 and (digits >= 7).mean() >= 0.9 and by_name != ("id", False):
            return ColumnGuess("string", "phone", True, 0.9)

    if by_name is not None:
        semantic, pii = by_name
        # the name says "amount" but values are text: keep the type honest
        if semantic in ("currency_amount", "quantity", "percentage") and data_type not in ("integer", "float", "decimal"):
            semantic, pii = "generic_string", False
        else:
            if semantic == "currency_amount" and data_type == "float":
                data_type = "decimal"
            return ColumnGuess(data_type, semantic, pii, 0.8 if semantic != "id" else 0.9, parsed)

    if data_type in ("date", "datetime"):
        return ColumnGuess(data_type, data_type, False, 0.85, parsed)
    if data_type == "decimal" and parsed is not None and values.astype(str).str.match(_CURRENCY).mean() >= 0.9:
        return ColumnGuess(data_type, "currency_amount", False, 0.9, parsed)
    if data_type in ("integer", "float", "decimal"):
        return ColumnGuess(data_type, "generic_number", False, 0.5, parsed)
    if data_type == "string" and not values.empty:
        distinct = values.nunique()
        if distinct <= CATEGORY_MAX_DISTINCT and distinct < max(2, len(values) * 0.5):
            return ColumnGuess(data_type, "category", False, 0.6, parsed)
        if values.astype(str).str.len().mean() > 40:
            return ColumnGuess(data_type, "text", False, 0.5, parsed)
    return ColumnGuess(data_type, "generic_string", False, 0.4, parsed)
