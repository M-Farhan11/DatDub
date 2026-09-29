"""Scenario, validation report and ground-truth contract models."""

from typing import Literal

from pydantic import BaseModel, Field

ScenarioKind = Literal["null_burst", "extreme_value", "duplicate_record", "boundary_date", "rule_violation"]

CheckStatus = Literal["PASS", "FAIL"]


class ScenarioProposal(BaseModel):
    id: str
    kind: ScenarioKind
    table: str
    column: str | None = None
    rule_id: str | None = None
    title: str
    suggested_count: int = Field(default=5, ge=1)
    description: str = ""
    expected_behavior: str = ""


class ScenarioSelection(BaseModel):
    proposal: ScenarioProposal
    count: int = Field(default=5, ge=1, le=1000)


class ValidationCheck(BaseModel):
    name: str
    table: str
    status: CheckStatus
    score: float = Field(ge=0.0, le=1.0)
    detail: str = ""
    expected_violations: int = 0


class Similarity(BaseModel):
    overall: float = Field(ge=0.0, le=1.0)
    per_column: dict[str, float] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    overall: CheckStatus
    checks: list[ValidationCheck] = Field(default_factory=list)
    # null when no sample profile exists
    similarity: Similarity | None = None


class GroundTruthEntry(BaseModel):
    scenario_id: str
    kind: ScenarioKind
    table: str
    affected_ids: list[str]
    description: str = ""
    expected_behavior: str = ""
