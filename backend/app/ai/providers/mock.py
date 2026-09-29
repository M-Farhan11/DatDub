"""Mock AI provider.

Makes no external calls and needs no API key. Returns valid JSON for every
structured model, derived from the prompt's `context` with simple
heuristics, so the full demo works offline (AI_PROVIDER=mock).
"""

import re
from typing import Any

from pydantic import BaseModel

from app.ai.schemas import (
    AIPrompt,
    ColumnSemantics,
    DraftColumn,
    DraftForeignKey,
    DraftRule,
    DraftScenario,
    DraftTable,
    ScenarioPlan,
    SchemaDraft,
    SemanticEnrichment,
)
from app.schemas.dataset import DatasetSchema


class MockProvider:
    name = "mock"

    async def generate_json(self, prompt: AIPrompt, response_model: type[BaseModel]) -> str:
        if response_model is SchemaDraft:
            result: BaseModel = _schema_draft(prompt.context.get("prompt", ""))
        elif response_model is SemanticEnrichment:
            result = _enrichment(prompt.context.get("tables", []))
        elif response_model is ScenarioPlan:
            result = _scenario_plan(prompt.context.get("schema", {}))
        else:
            raise NotImplementedError(f"MockProvider has no canned {response_model.__name__}")
        return result.model_dump_json()


# --- schema draft: the closest built-in template -----------------------------


def _schema_draft(user_prompt: str) -> SchemaDraft:
    from app.templates import get_template  # local import: templates are not an AI dependency

    finance = re.search(r"invoice|financ|billing|account|bank", user_prompt, re.I)
    template = get_template("finance" if finance else "ecommerce")
    draft = _schema_to_draft(template)
    draft.notes.append(f"Mock AI: used the built-in {'finance' if finance else 'e-commerce'} schema.")
    return draft


def _schema_to_draft(schema: DatasetSchema) -> SchemaDraft:
    tables = [
        DraftTable(
            name=t.name,
            primary_key=t.primary_key,
            columns=[
                DraftColumn(
                    name=c.name,
                    data_type=c.data_type,
                    semantic_type=c.semantic_type,
                    nullable=c.nullable,
                    unique=c.unique,
                    pii=c.pii,
                    allowed_values=c.allowed_values,
                    min=c.min if isinstance(c.min, int | float) else None,
                    max=c.max if isinstance(c.max, int | float) else None,
                )
                for c in t.columns
            ],
            foreign_keys=[
                DraftForeignKey(
                    column=fk.column,
                    ref_table=fk.ref_table,
                    ref_column=fk.ref_column,
                    min_children=fk.min_children,
                    max_children=fk.max_children,
                )
                for fk in t.foreign_keys
            ],
        )
        for t in schema.tables
    ]
    rules = [
        DraftRule(
            kind=r.kind,
            table=r.table,
            column=r.column,
            description=r.description,
            **{k: v for k, v in r.params.items() if k in DraftRule.model_fields and k not in ("table", "column")},
        )
        for r in schema.rules
    ]
    return SchemaDraft(name=schema.name, tables=tables, rules=rules)


# --- semantic enrichment: name heuristics ------------------------------------

_NAME_RULES: list[tuple[str, str, bool]] = [
    (r"e_?mail", "email", True),
    (r"phone|mobile|tel", "phone", True),
    (r"first_?name", "first_name", True),
    (r"last_?name|surname", "last_name", True),
    (r"^(full_?)?name$|customer_?name|person", "person_name", True),
    (r"iban|account_?number", "iban", True),
    (r"address|street", "address", True),
    (r"city", "city", False),
    (r"country", "country", False),
    (r"company|organi[sz]ation|employer", "company", False),
    (r"url|website|link", "url", False),
    (r"sku|product_?code", "sku", False),
    (r"status|state$", "status", False),
    (r"type|category|method|segment|currency", "category", False),
    (r"amount|price|total|cost|balance|revenue|salary|fee", "currency_amount", False),
    (r"qty|quantity|count", "quantity", False),
    (r"pct|percent|rate$", "percentage", False),
    (r"_id$|^id$", "id", False),
]


def _enrichment(tables: list[dict[str, Any]]) -> SemanticEnrichment:
    out: list[ColumnSemantics] = []
    for table in tables:
        for col in table.get("columns", []):
            name = str(col.get("name", ""))
            semantic, pii, confidence = _guess(name.lower(), str(col.get("data_type", "string")))
            out.append(
                ColumnSemantics(table=table.get("name", ""), column=name, semantic_type=semantic, pii=pii, confidence=confidence)
            )
    return SemanticEnrichment(columns=out)


def _guess(name: str, data_type: str) -> tuple[Any, bool, float]:
    for pattern, semantic, pii in _NAME_RULES:
        if re.search(pattern, name):
            return semantic, pii, 0.8
    if data_type in ("date", "datetime"):
        return data_type, False, 0.7
    if data_type in ("integer", "float", "decimal"):
        return "generic_number", False, 0.5
    return "generic_string", False, 0.4


# --- scenario plan: one proposal per kind that fits --------------------------


def _scenario_plan(summary: dict[str, Any]) -> ScenarioPlan:
    tables = summary.get("tables", [])
    proposals: list[DraftScenario] = []

    rule = next((r for r in summary.get("rules", []) if r["kind"] == "lte_parent"), None)
    rule = rule or next((r for r in summary.get("rules", []) if r["kind"] in ("date_order", "sum_of_children")), None)
    if rule:
        proposals.append(
            DraftScenario(
                kind="rule_violation",
                table=rule["table"],
                rule_id=rule["id"],
                title=f"Break rule: {rule['table']}.{rule['column']}",
                suggested_count=5,
                description=f"Records that violate: {rule['description'] or rule['kind']}",
                expected_behavior="The application should detect and flag these records.",
            )
        )

    def first(pred):
        for t in tables:
            for c in t["columns"]:
                if c["name"] != t["primary_key"] and pred(c):
                    return t, c
        return None

    if hit := first(lambda c: c["nullable"]):
        t, c = hit
        proposals.append(
            DraftScenario(
                kind="null_burst",
                table=t["name"],
                column=c["name"],
                title=f"Missing {c['name']} values",
                suggested_count=10,
                description=f"A burst of NULL {t['name']}.{c['name']} values",
                expected_behavior="The application should handle missing values without crashing.",
            )
        )
    if hit := first(lambda c: c["semantic_type"] == "currency_amount"):
        t, c = hit
        proposals.append(
            DraftScenario(
                kind="extreme_value",
                table=t["name"],
                column=c["name"],
                title=f"Extreme {c['name']}",
                suggested_count=3,
                description=f"{t['name']}.{c['name']} values far outside the normal range",
                expected_behavior="The application should flag or cap abnormal amounts.",
            )
        )
    if hit := first(lambda c: c["data_type"] in ("date", "datetime")):
        t, c = hit
        proposals.append(
            DraftScenario(
                kind="boundary_date",
                table=t["name"],
                column=c["name"],
                title=f"Boundary {c['name']} dates",
                suggested_count=5,
                description=f"{t['name']}.{c['name']} on month ends, leap days and far past/future",
                expected_behavior="Date handling should stay correct at calendar boundaries.",
            )
        )
    leaf = next((t for t in tables if t["name"] == "payments"), None) or (tables[-1] if tables else None)
    if leaf:
        proposals.append(
            DraftScenario(
                kind="duplicate_record",
                table=leaf["name"],
                title=f"Duplicate {leaf['name']} records",
                suggested_count=4,
                description=f"Copies of existing {leaf['name']} rows with new primary keys",
                expected_behavior="The application should detect likely duplicates.",
            )
        )
    return ScenarioPlan(proposals=proposals)
