"""Scenario proposals.

F0 STUB: deterministic proposals derived from the schema. F7 replaces this
with AI proposals validated against the schema.
"""

from fastapi import APIRouter

from app.schemas import ProposeScenariosRequest, ProposeScenariosResponse, ScenarioProposal

router = APIRouter(tags=["scenarios"])


@router.post("/scenarios/propose", response_model=ProposeScenariosResponse)
def propose(req: ProposeScenariosRequest) -> ProposeScenariosResponse:
    schema = req.schema_
    proposals: list[ScenarioProposal] = []

    for rule in schema.rules:
        if rule.kind == "lte_parent":
            proposals.append(
                ScenarioProposal(
                    id=f"s{len(proposals) + 1}",
                    kind="rule_violation",
                    table=rule.table,
                    column=rule.column,
                    rule_id=rule.id,
                    title=f"{rule.table}.{rule.column} exceeds {rule.params.get('parent_table')}",
                    description=f"Break rule {rule.id}: {rule.description}",
                    expected_behavior="The application should flag the overpayment.",
                )
            )
            break

    for table in schema.tables:
        nullable = next((c for c in table.columns if c.nullable), None)
        if nullable:
            proposals.append(
                ScenarioProposal(
                    id=f"s{len(proposals) + 1}",
                    kind="null_burst",
                    table=table.name,
                    column=nullable.name,
                    title=f"Missing {nullable.name} values",
                    description=f"A burst of NULL {table.name}.{nullable.name} values",
                    expected_behavior="The application should handle missing values gracefully.",
                )
            )
            break

    for table in schema.tables:
        amount = next((c for c in table.columns if c.semantic_type == "currency_amount"), None)
        if amount:
            proposals.append(
                ScenarioProposal(
                    id=f"s{len(proposals) + 1}",
                    kind="extreme_value",
                    table=table.name,
                    column=amount.name,
                    title=f"Extreme {amount.name}",
                    description=f"Values of {table.name}.{amount.name} far outside the normal range",
                    expected_behavior="The application should flag or cap abnormal amounts.",
                )
            )
            break

    return ProposeScenariosResponse(proposals=proposals)
