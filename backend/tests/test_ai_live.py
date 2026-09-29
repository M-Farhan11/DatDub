"""Live AI smoke tests. Skipped unless the provider's key + model are set in .env.

Each test makes ONE real call and checks that it returns a valid object.
Rate limits / overload on the provider side (HTTP 429 / 503) are reported
as skips with the reason: they are quota issues, not code bugs. Invalid
output still fails.

Run: pytest tests/test_ai_live.py -v -rs
"""

import httpx
import pytest
from google.genai import errors as genai_errors

from app.ai import prompts
from app.ai.schemas import ScenarioPlan, SchemaDraft
from app.ai.service import build_provider
from app.ai.validate import draft_to_schema, validate_proposals
from app.core.config import Settings
from app.templates import get_template

SETTINGS = Settings()
TRANSIENT = {429, 503}


async def _call(provider_name, prompt, response_model):
    provider = build_provider(provider_name, SETTINGS)
    if provider is None:
        pytest.skip(f"{provider_name} key/model not configured")
    try:
        raw = await provider.generate_json(prompt, response_model)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in TRANSIENT:
            pytest.skip(f"{provider_name} rate-limited/overloaded ({exc.response.status_code})")
        raise
    except genai_errors.APIError as exc:
        if exc.code in TRANSIENT:
            pytest.skip(f"{provider_name} rate-limited/overloaded ({exc.code})")
        raise
    return response_model.model_validate_json(raw)


@pytest.mark.parametrize("provider", ["gemini", "groq"])
async def test_live_prompt_to_schema(provider):
    draft = await _call(provider, prompts.schema_draft_prompt("A clinic with patients, appointments and invoices"), SchemaDraft)
    schema, _ = draft_to_schema(draft)
    assert len(schema.tables) >= 2


@pytest.mark.parametrize("provider", ["gemini", "groq"])
async def test_live_scenario_plan(provider):
    finance = get_template("finance")
    plan = await _call(provider, prompts.scenario_plan_prompt(finance, "Add realistic edge cases"), ScenarioPlan)
    assert validate_proposals(plan, finance)
