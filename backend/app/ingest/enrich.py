"""AI semantic enrichment for ingested schemas (CSV, Postgres, SQLite).

`build_ai_payload` is the privacy boundary: it sends column names, data
types and aggregates only. PII columns send no statistics at all. Category
values are sent only for non-PII columns already recognised as
category/status/boolean, and only when every value looks like a short label
(free text such as notes or diagnoses never leaves). PK and FK columns are
left out (they stay `id`).
"""

import re
from typing import Any

from app.ai.prompts import semantic_enrichment_prompt
from app.ai.schemas import SemanticEnrichment
from app.ai.service import get_ai_service
from app.ai.validate import apply_enrichment
from app.core.exceptions import AIProviderError
from app.ingest.heuristics import CATEGORY_MAX_DISTINCT, STRONG, is_pii_semantic
from app.schemas.dataset import ColumnSchema, DatasetSchema

LABEL_MAX_CHARS = 24
LABEL_MAX_WORDS = 3
# a label is letters/digits with simple separators; no @, no long digit runs (codes, phone numbers)
_LABEL = re.compile(r"^[^\W_][\w .&/+-]*$")
_DIGIT_RUN = re.compile(r"\d{4,}")


def build_ai_payload(schema: DatasetSchema) -> list[dict[str, Any]]:
    tables = []
    for t in schema.tables:
        keys = {t.primary_key} | {fk.column for fk in t.foreign_keys}
        columns = []
        for c in t.columns:
            if c.name in keys:
                continue
            entry: dict[str, Any] = {"name": c.name, "data_type": c.data_type}
            pii = c.pii or is_pii_semantic(c.semantic_type)
            p = c.profile
            if p is not None and not pii:
                stats: dict[str, Any] = {"null_rate": p.null_rate}
                if p.unique_ratio is not None:
                    stats["unique_ratio"] = p.unique_ratio
                if c.data_type in ("integer", "float", "decimal", "date", "datetime"):
                    stats.update({k: v for k, v in (("min", p.min), ("max", p.max), ("mean", p.mean)) if v is not None})
                entry["stats"] = stats
                labels = _shareable_labels(c)
                if labels:
                    entry["categories"] = labels
            columns.append(entry)
        if columns:
            tables.append({"name": t.name, "columns": columns})
    return tables


def _shareable_labels(c: ColumnSchema) -> list[str] | None:
    """Category values that may go to the AI, or None."""
    p = c.profile
    if p is None or not p.top_values or len(p.top_values) >= CATEGORY_MAX_DISTINCT:
        return None
    if c.data_type != "boolean" and c.semantic_type not in ("category", "status"):
        return None
    values = [str(v) for v, _ in p.top_values]
    if all(_is_label(v) for v in values):
        return values
    return None


def _is_label(v: str) -> bool:
    return (
        len(v) <= LABEL_MAX_CHARS
        and len(v.split()) <= LABEL_MAX_WORDS
        and bool(_LABEL.match(v))
        and not _DIGIT_RUN.search(v)
    )


async def enrich_schema(schema: DatasetSchema) -> list[str]:
    """Apply AI semantics in place. Falls back to the heuristics when AI is unavailable."""
    payload = build_ai_payload(schema)
    if not payload:
        return []
    try:
        enrichment = await get_ai_service().generate_structured(semantic_enrichment_prompt(payload), SemanticEnrichment)
    except AIProviderError:
        return ["AI enrichment was unavailable, so column types come from heuristics only."]
    applied = apply_enrichment(schema, enrichment, keep_above=STRONG)
    return [f"AI labelled {applied} column(s) from names and aggregate statistics (no rows were sent)."]
