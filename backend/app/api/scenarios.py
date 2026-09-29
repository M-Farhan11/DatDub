"""Scenario proposals: AI picks from the scenario catalogue; invalid proposals are dropped."""

from fastapi import APIRouter

from app.ai.prompts import scenario_plan_prompt
from app.ai.schemas import ScenarioPlan
from app.ai.service import get_ai_service
from app.ai.validate import validate_proposals
from app.schemas import ProposeScenariosRequest, ProposeScenariosResponse

router = APIRouter(tags=["scenarios"])


@router.post("/scenarios/propose", response_model=ProposeScenariosResponse)
async def propose(req: ProposeScenariosRequest) -> ProposeScenariosResponse:
    plan = await get_ai_service().generate_structured(scenario_plan_prompt(req.schema_, req.instruction), ScenarioPlan)
    return ProposeScenariosResponse(proposals=validate_proposals(plan, req.schema_))
