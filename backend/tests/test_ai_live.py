"""Live AI smoke tests. Skipped unless the provider's key + model are set in the env / .env.

Run: pytest tests/test_ai_live.py -v
"""

import pytest

from app.ai import prompts
from app.ai.schemas import ScenarioPlan, SchemaDraft
from app.ai.service import AIService, build_provider
from app.ai.validate import draft_to_schema, validate_proposals
from app.core.config import Settings
from app.templates import get_template

SETTINGS = Settings()


@pytest.mark.parametrize("provider", ["gemini", "groq"])
async def test_live_prompt_to_schema_and_scenarios(provider):
    if build_provider(provider, SETTINGS) is None:
        pytest.skip(f"{provider} key/model not configured")
    service = AIService(settings=SETTINGS.model_copy(update={"ai_provider": provider, "ai_fallback_provider": ""}))
    assert service.provider_name == provider

    draft = await service.generate_structured(
        prompts.schema_draft_prompt("A clinic with patients, appointments and invoices"), SchemaDraft
    )
    schema, _ = draft_to_schema(draft)
    assert len(schema.tables) >= 2

    finance = get_template("finance")
    plan = await service.generate_structured(prompts.scenario_plan_prompt(finance, "Add realistic edge cases"), ScenarioPlan)
    assert validate_proposals(plan, finance)
