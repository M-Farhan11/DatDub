import json

import httpx
import pytest

from app.ai import prompts
from app.ai.providers import groq as groq_module
from app.ai.providers.groq import GroqProvider
from app.ai.providers.mock import MockProvider
from app.ai.schemas import (
    AIPrompt,
    DraftColumn,
    DraftForeignKey,
    DraftRule,
    DraftScenario,
    DraftTable,
    ScenarioPlan,
    SchemaDraft,
    SemanticEnrichment,
)
from app.ai.service import AIService
from app.ai.validate import apply_enrichment, draft_to_schema, validate_proposals
from app.core.config import Settings
from app.core.exceptions import AIProviderError
from app.schemas import ColumnProfile
from app.templates import get_template


class ScriptedProvider:
    """Returns the scripted answers in order; an Exception entry is raised."""

    def __init__(self, name: str, answers: list) -> None:
        self.name = name
        self.answers = list(answers)
        self.calls: list[AIPrompt] = []

    async def generate_json(self, prompt, response_model):
        self.calls.append(prompt)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


VALID_PLAN = ScenarioPlan(
    proposals=[DraftScenario(kind="duplicate_record", table="payments", title="Dup payments")]
).model_dump_json()


def _service(primary, fallback=None) -> AIService:
    service = AIService(settings=Settings(ai_provider="mock"))
    service._primary = primary
    service._fallback = fallback
    return service


def _plan_prompt() -> AIPrompt:
    return prompts.scenario_plan_prompt(get_template("finance"), "edge cases")


# --- AIService: validation, retry, fallback ----------------------------------


async def test_valid_output_is_returned_as_model():
    primary = ScriptedProvider("p", [VALID_PLAN])
    plan = await _service(primary).generate_structured(_plan_prompt(), ScenarioPlan)
    assert isinstance(plan, ScenarioPlan)
    assert len(primary.calls) == 1


async def test_invalid_output_is_retried_once_with_feedback():
    primary = ScriptedProvider("p", ["not json", VALID_PLAN])
    plan = await _service(primary).generate_structured(_plan_prompt(), ScenarioPlan)
    assert plan.proposals[0].kind == "duplicate_record"
    assert len(primary.calls) == 2
    assert "previous answer was invalid" in primary.calls[1].user


async def test_invalid_twice_goes_to_fallback():
    primary = ScriptedProvider("p", ['{"proposals": [{"kind": "bogus"}]}', "{}"])
    fallback = ScriptedProvider("f", [VALID_PLAN])
    plan = await _service(primary, fallback).generate_structured(_plan_prompt(), ScenarioPlan)
    assert len(plan.proposals) == 1
    assert len(primary.calls) == 2 and len(fallback.calls) == 1


async def test_provider_error_skips_retry_and_uses_fallback():
    primary = ScriptedProvider("p", [RuntimeError("down")])
    fallback = ScriptedProvider("f", [VALID_PLAN])
    await _service(primary, fallback).generate_structured(_plan_prompt(), ScenarioPlan)
    assert len(primary.calls) == 1 and len(fallback.calls) == 1


async def test_everything_failing_raises_controlled_error():
    primary = ScriptedProvider("p", ["bad", "bad"])
    fallback = ScriptedProvider("f", [RuntimeError("down")])
    with pytest.raises(AIProviderError):
        await _service(primary, fallback).generate_structured(_plan_prompt(), ScenarioPlan)


async def test_markdown_fences_are_tolerated():
    primary = ScriptedProvider("p", [f"```json\n{VALID_PLAN}\n```"])
    plan = await _service(primary).generate_structured(_plan_prompt(), ScenarioPlan)
    assert len(plan.proposals) == 1


def test_real_provider_without_key_falls_back_to_mock():
    service = AIService(settings=Settings(ai_provider="gemini", gemini_api_key="", ai_fallback_provider="groq", groq_api_key=""))
    assert service.provider_name == "mock"
    assert service._fallback is None


def test_unknown_provider_falls_back_to_mock():
    assert AIService(settings=Settings(ai_provider="does-not-exist")).provider_name == "mock"


# --- MockProvider: canned objects for every structured model ------------------


async def test_mock_prompt_to_schema_finance():
    service = AIService(settings=Settings(ai_provider="mock"))
    draft = await service.generate_structured(prompts.schema_draft_prompt("Invoices for a SaaS company"), SchemaDraft)
    schema, notes = draft_to_schema(draft)
    template = get_template("finance")
    assert [t.name for t in schema.tables] == [t.name for t in template.tables]
    assert len(schema.rules) == len(template.rules)
    assert schema.document_hints and schema.document_hints.invoice.items_table == "invoice_items"
    assert schema.source == "prompt"
    assert any("Mock AI" in n for n in notes)


async def test_mock_prompt_to_schema_ecommerce():
    service = AIService(settings=Settings(ai_provider="mock"))
    draft = await service.generate_structured(prompts.schema_draft_prompt("An online shop"), SchemaDraft)
    schema, _ = draft_to_schema(draft)
    assert "orders" in {t.name for t in schema.tables}


async def test_mock_semantic_enrichment():
    tables = [{"name": "people", "columns": [{"name": "email_address", "data_type": "string"},
                                             {"name": "signup", "data_type": "date"}]}]
    service = AIService(settings=Settings(ai_provider="mock"))
    result = await service.generate_structured(prompts.semantic_enrichment_prompt(tables), SemanticEnrichment)
    by_col = {c.column: c for c in result.columns}
    assert by_col["email_address"].semantic_type == "email" and by_col["email_address"].pii
    assert by_col["signup"].semantic_type == "date"


async def test_mock_scenario_plan_is_valid_for_the_schema():
    schema = get_template("finance")
    service = AIService(settings=Settings(ai_provider="mock"))
    plan = await service.generate_structured(prompts.scenario_plan_prompt(schema, "edge cases"), ScenarioPlan)
    proposals = validate_proposals(plan, schema)
    assert len(proposals) == len(plan.proposals) >= 4
    assert {p.kind for p in proposals} >= {"rule_violation", "extreme_value", "duplicate_record"}


# --- validate: invalid references are dropped ---------------------------------


def test_draft_with_bad_references_is_repaired():
    draft = SchemaDraft(
        name="My Shop",
        tables=[
            DraftTable(name="customers", primary_key="customer_id",
                       columns=[DraftColumn(name="name", data_type="string")]),
            DraftTable(name="orders", primary_key="order_id",
                       columns=[DraftColumn(name="order_id", data_type="string"),
                                DraftColumn(name="total", data_type="decimal"),
                                DraftColumn(name="created", data_type="date")],
                       foreign_keys=[DraftForeignKey(column="customer_id", ref_table="customers", ref_column="x"),
                                     DraftForeignKey(column="ghost_id", ref_table="ghosts", ref_column="ghost_id")]),
        ],
        rules=[
            DraftRule(kind="range", table="orders", column="total", min=0, max=500),
            DraftRule(kind="range", table="orders", column="nope", min=0, max=1),
            DraftRule(kind="date_order", table="orders", column="created", before="missing"),
            DraftRule(kind="lte_parent", table="orders", column="total", parent_table="customers", parent_column="zzz"),
        ],
    )
    schema, notes = draft_to_schema(draft)
    customers, orders = schema.tables
    assert schema.name == "my_shop"
    assert customers.columns[0].name == "customer_id" and customers.columns[0].unique
    assert [fk.column for fk in orders.foreign_keys] == ["customer_id"]
    assert orders.foreign_keys[0].ref_column == "customer_id"
    assert any(c.name == "customer_id" for c in orders.columns)
    assert [r.kind for r in schema.rules] == ["range"]
    assert sum("Dropped rule" in n for n in notes) == 3
    assert any("ghosts" in n for n in notes)


def test_fk_cycle_is_dropped():
    draft = SchemaDraft(
        name="cyc",
        tables=[
            DraftTable(name="a", primary_key="a_id", columns=[], foreign_keys=[DraftForeignKey(column="b_id", ref_table="b", ref_column="b_id")]),
            DraftTable(name="b", primary_key="b_id", columns=[], foreign_keys=[DraftForeignKey(column="a_id", ref_table="a", ref_column="a_id")]),
        ],
    )
    schema, notes = draft_to_schema(draft)
    assert sum(len(t.foreign_keys) for t in schema.tables) == 1
    assert any("cycle" in n for n in notes)


def test_invalid_proposals_are_dropped():
    schema = get_template("finance")
    plan = ScenarioPlan(
        proposals=[
            DraftScenario(kind="null_burst", table="customers", column="phone", title="ok"),
            DraftScenario(kind="null_burst", table="customers", column="nonexistent", title="bad column"),
            DraftScenario(kind="extreme_value", table="customers", column="email", title="not numeric"),
            DraftScenario(kind="rule_violation", table="payments", rule_id="r999", title="bad rule"),
            DraftScenario(kind="rule_violation", table="payments", rule_id="r3", title="ok rule"),
            DraftScenario(kind="duplicate_record", table="ghosts", title="bad table"),
        ]
    )
    proposals = validate_proposals(plan, schema)
    assert [p.title for p in proposals] == ["ok", "ok rule"]
    assert [p.id for p in proposals] == ["s1", "s2"]
    assert proposals[1].column == "amount"


def test_enrichment_skips_keys_and_unknown_columns():
    schema = get_template("finance")
    enrichment = SemanticEnrichment.model_validate(
        {"columns": [
            {"table": "customers", "column": "company", "semantic_type": "text", "pii": True, "confidence": 0.3},
            {"table": "customers", "column": "customer_id", "semantic_type": "email", "pii": True, "confidence": 1},
            {"table": "ghosts", "column": "x", "semantic_type": "email", "pii": True, "confidence": 1},
        ]}
    )
    assert apply_enrichment(schema, enrichment) == 1
    company = next(c for c in schema.table("customers").columns if c.name == "company")
    assert company.semantic_type == "text" and company.confidence == 0.3
    assert schema.table("customers").columns[0].semantic_type == "id"


# --- privacy + providers -------------------------------------------------------


def test_scenario_prompt_contains_no_profile_values():
    schema = get_template("finance")
    schema.table("customers").columns[1].profile = ColumnProfile(top_values=[("Jane SECRET Doe", 0.1)])
    prompt = prompts.scenario_plan_prompt(schema, "edge cases")
    assert "SECRET" not in prompt.user and "SECRET" not in json.dumps(prompt.context)


async def test_groq_provider_sends_json_mode_and_returns_content(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json={"choices": [{"message": {"content": VALID_PLAN}}]})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        groq_module.httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)
    )
    raw = await GroqProvider("k", "some-model").generate_json(_plan_prompt(), ScenarioPlan)
    assert ScenarioPlan.model_validate_json(raw)
    assert seen["body"]["model"] == "some-model"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert "proposals" in seen["body"]["messages"][0]["content"]  # schema embedded in system prompt
    assert seen["auth"] == "Bearer k"


async def test_mock_rejects_unknown_models():
    with pytest.raises(NotImplementedError):
        await MockProvider().generate_json(_plan_prompt(), AIPrompt)


def test_provider_names_are_case_insensitive():
    service = AIService(settings=Settings(ai_provider="GEMINI", gemini_api_key="k", gemini_model="m"))
    assert service.provider_name == "gemini"
