"""Core contract model: DatasetSchema and its parts.

This is the one internal contract shared by every stage (ingest, review,
generation, validation, documents, export). Mirrored in
`frontend/src/api/types.ts` and documented in `docs/api-contract.md`.
Changing it requires both humans to agree.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

DataType = Literal["string", "integer", "float", "decimal", "boolean", "date", "datetime"]

SemanticType = Literal[
    "id",
    "person_name",
    "first_name",
    "last_name",
    "email",
    "phone",
    "address",
    "city",
    "country",
    "company",
    "date",
    "datetime",
    "currency_amount",
    "quantity",
    "percentage",
    "category",
    "status",
    "text",
    "url",
    "sku",
    "iban",
    "generic_number",
    "generic_string",
]

SourceKind = Literal["template", "prompt", "csv", "postgres", "sqlite"]

RuleKind = Literal["range", "allowed_values", "date_order", "sum_of_children", "lte_parent"]

Cardinality = Literal["1:1", "1:N"]


class ColumnProfile(BaseModel):
    """Aggregate statistics from sample rows. Never contains raw rows."""

    null_rate: float = 0.0
    mean: float | None = None
    std: float | None = None
    min: float | str | None = None
    max: float | str | None = None
    # 10 bins: [bin_start, bin_end, count]
    histogram: list[tuple[float, float, int]] | None = None
    # [value, frequency 0..1]; only for low-cardinality, non-PII columns
    top_values: list[tuple[str, float]] | None = None
    unique_ratio: float | None = None


class ColumnSchema(BaseModel):
    name: str
    data_type: DataType
    semantic_type: SemanticType = "generic_string"
    nullable: bool = False
    unique: bool = False
    pii: bool = False
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    allowed_values: list[str] | None = None
    min: float | str | None = None
    max: float | str | None = None
    profile: ColumnProfile | None = None


class ForeignKey(BaseModel):
    column: str
    ref_table: str
    ref_column: str
    cardinality: Cardinality = "1:N"
    min_children: int = Field(default=0, ge=0)
    max_children: int = Field(default=10, ge=0)
    # children-per-parent distribution from the sample: [[n_children, frequency], ...]
    children_distribution: list[tuple[int, float]] | None = None


class TableSchema(BaseModel):
    name: str
    primary_key: str
    columns: list[ColumnSchema]
    foreign_keys: list[ForeignKey] = Field(default_factory=list)
    row_count_hint: int | None = None


class Rule(BaseModel):
    """A rule from the fixed catalogue.

    params per kind:
      range            {min, max}
      allowed_values   {values: [...]}
      date_order       {before: col_a, after: col_b, via_fk?: fk_column}
      sum_of_children  {child_table, expr}   expr = "col" or "a * b"
      lte_parent       {parent_table, parent_column}
    """

    id: str
    kind: RuleKind
    table: str
    column: str
    params: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class InvoiceHints(BaseModel):
    header_table: str
    items_table: str
    party_table: str


class DocumentHints(BaseModel):
    invoice: InvoiceHints | None = None


class DatasetSchema(BaseModel):
    name: str
    source: SourceKind
    tables: list[TableSchema]
    rules: list[Rule] = Field(default_factory=list)
    document_hints: DocumentHints | None = None

    def table(self, name: str) -> TableSchema | None:
        return next((t for t in self.tables if t.name == name), None)
