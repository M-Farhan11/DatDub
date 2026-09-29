"""AI-facing structured output models.

These are what the LLM is asked to return. They are deliberately flat (no
free-form dicts, no tuples) so they translate cleanly into the JSON schemas
Gemini and Groq accept. `app.ai.validate` converts them into the contract
models (`DatasetSchema`, `ScenarioProposal`) and drops invalid items.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.dataset import DataType, RuleKind, SemanticType
from app.schemas.report import ScenarioKind

AITask = Literal["schema_draft", "semantic_enrichment", "scenario_plan"]


class AIPrompt(BaseModel):
    """One structured AI call.

    `context` is the (already privacy-filtered) structured input that was
    rendered into `user`. Real providers ignore it; MockProvider uses it to
    return sensible canned output offline.
    """

    task: AITask
    system: str
    user: str
    context: dict[str, Any] = Field(default_factory=dict)


# --- prompt -> schema --------------------------------------------------------


class DraftColumn(BaseModel):
    name: str
    data_type: DataType
    semantic_type: SemanticType = "generic_string"
    nullable: bool = False
    unique: bool = False
    pii: bool = False
    allowed_values: list[str] | None = None
    min: float | None = None
    max: float | None = None


class DraftForeignKey(BaseModel):
    column: str
    ref_table: str
    ref_column: str
    min_children: int = 0
    max_children: int = 10


class DraftTable(BaseModel):
    name: str
    primary_key: str
    columns: list[DraftColumn]
    foreign_keys: list[DraftForeignKey] = Field(default_factory=list)


class DraftRule(BaseModel):
    """Flat rule; only the fields for its `kind` are used (see the rule catalogue)."""

    kind: RuleKind
    table: str
    column: str
    description: str = ""
    # range
    min: float | None = None
    max: float | None = None
    # allowed_values
    values: list[str] | None = None
    # date_order: before <= column; `before` is in the FK parent when via_fk is set
    before: str | None = None
    via_fk: str | None = None
    # sum_of_children
    child_table: str | None = None
    expr: str | None = None
    # lte_parent
    parent_table: str | None = None
    parent_column: str | None = None


class SchemaDraft(BaseModel):
    name: str
    tables: list[DraftTable] = Field(min_length=1)
    rules: list[DraftRule] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


# --- semantic enrichment -----------------------------------------------------


class ColumnSemantics(BaseModel):
    table: str
    column: str
    semantic_type: SemanticType
    pii: bool
    confidence: float = Field(ge=0.0, le=1.0)


class SemanticEnrichment(BaseModel):
    columns: list[ColumnSemantics]


# --- scenario proposals ------------------------------------------------------


class DraftScenario(BaseModel):
    kind: ScenarioKind
    table: str
    column: str | None = None
    rule_id: str | None = None
    title: str
    suggested_count: int = Field(default=5, ge=1, le=1000)
    description: str = ""
    expected_behavior: str = ""


class ScenarioPlan(BaseModel):
    proposals: list[DraftScenario]
