"""Request/response models for every endpoint in docs/api-contract.md."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.dataset import DatasetSchema
from app.schemas.report import GroundTruthEntry, ScenarioProposal, ScenarioSelection, ValidationReport


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class HealthResponse(BaseModel):
    status: str = "ok"


# --- templates ---------------------------------------------------------------


class TemplateSummary(BaseModel):
    id: str
    name: str
    description: str
    tables: int


# --- schema inference --------------------------------------------------------


class PromptSchemaRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=4000)


class SchemaResponse(BaseModel):
    """Response of from-prompt and from-csv."""

    schema_: DatasetSchema = Field(alias="schema")
    notes: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class DbConnection(BaseModel):
    """Send either `url` or the individual fields. Never stored or echoed back."""

    url: str | None = None
    host: str | None = None
    port: int = 5432
    database: str | None = None
    user: str | None = None
    password: str | None = Field(default=None, repr=False)
    sslmode: str | None = None

    model_config = {"hide_input_in_errors": True}

    @model_validator(mode="after")
    def _url_or_fields(self) -> "DbConnection":
        if not self.url and not (self.host and self.database and self.user):
            raise ValueError("Provide either `url` or host, database and user")
        return self

    def __repr__(self) -> str:  # never leak credentials through logs
        return "DbConnection(<redacted>)"

    __str__ = __repr__


class DbTablesRequest(BaseModel):
    connection: DbConnection


class DbTableInfo(BaseModel):
    name: str
    schema_: str = Field(default="public", alias="schema")
    column_count: int
    estimated_rows: int
    references: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class DbTablesResponse(BaseModel):
    tables: list[DbTableInfo]


ExtractMode = Literal["schema_only", "schema_and_sample"]


class FromDbRequest(BaseModel):
    connection: DbConnection
    tables: list[str] = Field(min_length=1)
    mode: ExtractMode = "schema_only"
    sample_limit: int = Field(default=200, ge=1, le=1000)


class FromDbResponse(BaseModel):
    """Response of from-db and from-sqlite."""

    schema_: DatasetSchema = Field(alias="schema")
    auto_added: list[str] = Field(default_factory=list)
    rows_sampled: int = 0
    notes: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


# --- scenarios ---------------------------------------------------------------


class ProposeScenariosRequest(BaseModel):
    schema_: DatasetSchema = Field(alias="schema")
    instruction: str = Field(default="Add realistic edge cases for testing", max_length=2000)

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class ProposeScenariosResponse(BaseModel):
    proposals: list[ScenarioProposal]


# --- generation --------------------------------------------------------------


class GenerateRequest(BaseModel):
    schema_: DatasetSchema = Field(alias="schema")
    # counts for root tables; child counts come from FK cardinality
    rows: dict[str, int] = Field(default_factory=dict)
    seed: int = 42
    null_rate: float = Field(default=0.0, ge=0.0, le=0.5)
    outlier_rate: float = Field(default=0.0, ge=0.0, le=0.5)
    locale: str = "en_US"
    scenarios: list[ScenarioSelection] = Field(default_factory=list)

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class GenerateResponse(BaseModel):
    dataset_id: str
    row_counts: dict[str, int]
    # 50 rows per table max
    previews: dict[str, list[dict[str, Any]]]
    report: ValidationReport
    ground_truth: list[GroundTruthEntry] = Field(default_factory=list)


# --- datasets ----------------------------------------------------------------


class TablePage(BaseModel):
    table: str
    total: int
    rows: list[dict[str, Any]]


class InvoiceListResponse(BaseModel):
    invoice_ids: list[str]
