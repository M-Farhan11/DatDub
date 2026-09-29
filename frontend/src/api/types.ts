// API contract v1.0: TypeScript mirror of backend/app/schemas/.
// OWNER: Farhan. Do not edit without agreement (see TASKS.md → Requests).
// Spec: docs/api-contract.md

// ---------- core: DatasetSchema ----------

export type DataType = "string" | "integer" | "float" | "decimal" | "boolean" | "date" | "datetime";

export type SemanticType =
  | "id" | "person_name" | "first_name" | "last_name" | "email" | "phone" | "address"
  | "city" | "country" | "company" | "date" | "datetime" | "currency_amount" | "quantity"
  | "percentage" | "category" | "status" | "text" | "url" | "sku" | "iban"
  | "generic_number" | "generic_string";

export type SourceKind = "template" | "prompt" | "csv" | "postgres" | "sqlite";
export type RuleKind = "range" | "allowed_values" | "date_order" | "sum_of_children" | "lte_parent";
export type Cardinality = "1:1" | "1:N";

export interface ColumnProfile {
  null_rate: number;
  mean: number | null;
  std: number | null;
  min: number | string | null;
  max: number | string | null;
  /** 10 bins: [bin_start, bin_end, count] */
  histogram: [number, number, number][] | null;
  /** [value, frequency 0..1], low-cardinality non-PII columns only */
  top_values: [string, number][] | null;
  unique_ratio: number | null;
}

export interface ColumnSchema {
  name: string;
  data_type: DataType;
  semantic_type: SemanticType;
  nullable: boolean;
  unique: boolean;
  pii: boolean;
  /** 0..1 */
  confidence: number;
  allowed_values: string[] | null;
  min: number | string | null;
  max: number | string | null;
  profile: ColumnProfile | null;
}

export interface ForeignKey {
  column: string;
  ref_table: string;
  ref_column: string;
  cardinality: Cardinality;
  min_children: number;
  max_children: number;
  /** [n_children, frequency] from the sample, when one exists */
  children_distribution: [number, number][] | null;
}

export interface TableSchema {
  name: string;
  primary_key: string;
  columns: ColumnSchema[];
  foreign_keys: ForeignKey[];
  row_count_hint: number | null;
}

/**
 * params per kind:
 *   range            { min, max }
 *   allowed_values   { values: string[] }
 *   date_order       { before, after, via_fk? }   (before is in the FK parent when via_fk is set)
 *   sum_of_children  { child_table, expr }         (expr = "col" or "a * b")
 *   lte_parent       { parent_table, parent_column }
 */
export interface Rule {
  id: string;
  kind: RuleKind;
  table: string;
  column: string;
  params: Record<string, unknown>;
  description: string;
}

export interface InvoiceHints {
  header_table: string;
  items_table: string;
  party_table: string;
}

export interface DocumentHints {
  invoice: InvoiceHints | null;
}

export interface DatasetSchema {
  name: string;
  source: SourceKind;
  tables: TableSchema[];
  rules: Rule[];
  document_hints: DocumentHints | null;
}

// ---------- scenarios, report, ground truth ----------

export type ScenarioKind = "null_burst" | "extreme_value" | "duplicate_record" | "boundary_date" | "rule_violation";
export type CheckStatus = "PASS" | "FAIL";

export interface ScenarioProposal {
  id: string;
  kind: ScenarioKind;
  table: string;
  column: string | null;
  rule_id: string | null;
  title: string;
  suggested_count: number;
  description: string;
  expected_behavior: string;
}

export interface ScenarioSelection {
  proposal: ScenarioProposal;
  /** 1..1000 */
  count: number;
}

export interface ValidationCheck {
  name: string;
  table: string;
  status: CheckStatus;
  /** 0..1 */
  score: number;
  detail: string;
  expected_violations: number;
}

export interface Similarity {
  /** 0..1 */
  overall: number;
  /** "table.column" → 0..1 */
  per_column: Record<string, number>;
}

export interface ValidationReport {
  overall: CheckStatus;
  checks: ValidationCheck[];
  similarity: Similarity | null;
}

export interface GroundTruthEntry {
  scenario_id: string;
  kind: ScenarioKind;
  table: string;
  affected_ids: string[];
  description: string;
  expected_behavior: string;
}

// ---------- endpoints ----------

export interface ApiError {
  error: { code: string; message: string };
}

export interface HealthResponse {
  status: "ok";
}

/** GET /api/templates */
export interface TemplateSummary {
  id: string;
  name: string;
  description: string;
  tables: number;
}

/** POST /api/schema/from-prompt */
export interface PromptSchemaRequest {
  prompt: string;
}

/** Response of from-prompt and from-csv */
export interface SchemaResponse {
  schema: DatasetSchema;
  notes: string[];
}

/** Send either `url` or host/database/user(/password). Keep in memory only. */
export interface DbConnection {
  url?: string | null;
  host?: string | null;
  port?: number;
  database?: string | null;
  user?: string | null;
  password?: string | null;
  sslmode?: string | null;
}

/** POST /api/db/tables */
export interface DbTablesRequest {
  connection: DbConnection;
}

export interface DbTableInfo {
  name: string;
  schema: string;
  column_count: number;
  estimated_rows: number;
  references: string[];
}

export interface DbTablesResponse {
  tables: DbTableInfo[];
}

export type ExtractMode = "schema_only" | "schema_and_sample";

/** POST /api/schema/from-db */
export interface FromDbRequest {
  connection: DbConnection;
  tables: string[];
  mode: ExtractMode;
  /** default 200, max 1000; ignored in schema_only */
  sample_limit: number;
}

/** Response of from-db and from-sqlite */
export interface FromDbResponse {
  schema: DatasetSchema;
  auto_added: string[];
  rows_sampled: number;
  notes: string[];
}

/** POST /api/scenarios/propose */
export interface ProposeScenariosRequest {
  schema: DatasetSchema;
  instruction: string;
}

export interface ProposeScenariosResponse {
  proposals: ScenarioProposal[];
}

/** POST /api/generate */
export interface GenerateRequest {
  schema: DatasetSchema;
  /** counts for root tables; child counts come from cardinality */
  rows: Record<string, number>;
  seed: number;
  /** 0..0.5 */
  null_rate: number;
  /** 0..0.5 */
  outlier_rate: number;
  locale: string;
  scenarios: ScenarioSelection[];
}

export type Row = Record<string, string | number | boolean | null>;

export interface GenerateResponse {
  dataset_id: string;
  row_counts: Record<string, number>;
  /** max 50 rows per table */
  previews: Record<string, Row[]>;
  report: ValidationReport;
  ground_truth: GroundTruthEntry[];
}

/** GET /api/datasets/{id}/tables/{table}?offset&limit (limit max 500) */
export interface TablePage {
  table: string;
  total: number;
  rows: Row[];
}

/** GET /api/datasets/{id}/documents/invoices */
export interface InvoiceListResponse {
  invoice_ids: string[];
}
