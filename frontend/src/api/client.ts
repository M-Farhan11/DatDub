/**
 * API client: one typed function per endpoint in docs/api-contract.md.
 * With VITE_USE_FIXTURES=true the same functions return fixture data after a
 * short delay, so switching to the real backend is only an env change.
 */
import * as fx from "./fixtures"
import type {
  ApiError,
  DatasetSchema,
  DbConnection,
  DbTablesResponse,
  ExtractMode,
  FromDbRequest,
  FromDbResponse,
  GenerateRequest,
  GenerateResponse,
  InvoiceListResponse,
  ProposeScenariosResponse,
  SchemaResponse,
  TablePage,
  TemplateSummary,
} from "./types"

export const API_URL = (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "")
export const USE_FIXTURES = import.meta.env.VITE_USE_FIXTURES === "true"

/** Error thrown by every API function. `message` is safe to show in the UI. */
export class ApiRequestError extends Error {
  readonly code: string
  readonly status: number

  constructor(code: string, message: string, status: number) {
    super(message)
    this.name = "ApiRequestError"
    this.code = code
    this.status = status
  }
}

function isApiErrorBody(value: unknown): value is ApiError {
  if (typeof value !== "object" || value === null || !("error" in value)) return false
  const err = (value as { error: unknown }).error
  return typeof err === "object" && err !== null && "message" in err && "code" in err
}

async function toApiError(res: Response): Promise<ApiRequestError> {
  try {
    const body: unknown = await res.json()
    if (isApiErrorBody(body)) return new ApiRequestError(body.error.code, body.error.message, res.status)
  } catch {
    /* body was not JSON */
  }
  return new ApiRequestError("http_error", `The request failed (status ${res.status}).`, res.status)
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  let res: Response
  try {
    res = await fetch(`${API_URL}/api${path}`, init)
  } catch {
    throw new ApiRequestError(
      "network_error",
      "Could not reach the DatDub service. Check that the backend is running and try again.",
      0,
    )
  }
  if (!res.ok) throw await toApiError(res)
  return res
}

async function getJson<T>(path: string): Promise<T> {
  return (await (await send(path)).json()) as T
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await send(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  return (await res.json()) as T
}

async function postForm<T>(path: string, form: FormData): Promise<T> {
  return (await (await send(path, { method: "POST", body: form })).json()) as T
}

/** Fixture helper: resolves a deep copy after 400-900 ms so loading states show. */
function fixture<T>(value: T): Promise<T> {
  const ms = 400 + Math.round(Math.random() * 500)
  return new Promise((resolve) => setTimeout(() => resolve(structuredClone(value)), ms))
}

function fixtureError(code: string, message: string, status: number): Promise<never> {
  return new Promise((_, reject) => setTimeout(() => reject(new ApiRequestError(code, message, status)), 400))
}

const enc = encodeURIComponent

// ---------- templates ----------

export function getTemplates(): Promise<TemplateSummary[]> {
  return USE_FIXTURES ? fixture(fx.templates) : getJson("/templates")
}

export function getTemplate(id: string): Promise<DatasetSchema> {
  if (USE_FIXTURES) {
    const schema = fx.templateSchemas[id]
    return schema ? fixture(schema) : fixtureError("template_not_found", `Template "${id}" does not exist.`, 404)
  }
  return getJson(`/templates/${enc(id)}`)
}

// ---------- schema sources ----------

export function schemaFromPrompt(prompt: string): Promise<SchemaResponse> {
  return USE_FIXTURES ? fixture(fx.promptResponse) : postJson("/schema/from-prompt", { prompt })
}

export function schemaFromCsv(files: File[]): Promise<SchemaResponse> {
  if (USE_FIXTURES) return fixture(fx.csvResponse)
  const form = new FormData()
  for (const file of files) form.append("files", file)
  return postForm("/schema/from-csv", form)
}

/** Step A: list tables. Reads no rows. Credentials are sent, never stored. */
export function dbTables(connection: DbConnection): Promise<DbTablesResponse> {
  return USE_FIXTURES ? fixture(fx.dbTablesResponse) : postJson("/db/tables", { connection })
}

/** Steps B + C: extract the chosen tables (parents are auto-added by the backend). */
export function schemaFromDb(request: FromDbRequest): Promise<FromDbResponse> {
  if (USE_FIXTURES) {
    const parents = request.tables.includes("customers") ? [] : ["customers"]
    return fixture({ ...fx.fromDbResponse, auto_added: parents })
  }
  return postJson("/schema/from-db", request)
}

export function schemaFromSqlite(
  file: File,
  mode: ExtractMode,
  sampleLimit: number,
  tables: string[] = [],
): Promise<FromDbResponse> {
  if (USE_FIXTURES) return fixture(fx.fromSqliteResponse)
  const form = new FormData()
  form.append("file", file)
  form.append("mode", mode)
  form.append("sample_limit", String(sampleLimit))
  if (tables.length > 0) form.append("tables", tables.join(","))
  return postForm("/schema/from-sqlite", form)
}

// ---------- scenarios + generation ----------

export function proposeScenarios(schema: DatasetSchema, instruction: string): Promise<ProposeScenariosResponse> {
  return USE_FIXTURES ? fixture({ proposals: fx.proposals }) : postJson("/scenarios/propose", { schema, instruction })
}

export function generate(request: GenerateRequest): Promise<GenerateResponse> {
  if (USE_FIXTURES) {
    const tooLarge = Object.values(request.rows).some((n) => n > 100_000)
    if (tooLarge) {
      return fixtureError("rows_limit_exceeded", "Each table is limited to 100,000 rows. Lower the row count and try again.", 422)
    }
    return fixture(fx.generate(request))
  }
  return postJson("/generate", request)
}

// ---------- datasets ----------

export function getTablePage(datasetId: string, table: string, offset: number, limit = 50): Promise<TablePage> {
  if (USE_FIXTURES) {
    const page = fx.tablePage(datasetId, table, offset, limit)
    return page
      ? fixture(page)
      : fixtureError("dataset_not_found", "This dataset has expired or does not exist.", 404)
  }
  return getJson(`/datasets/${enc(datasetId)}/tables/${enc(table)}?offset=${offset}&limit=${limit}`)
}

export function listInvoices(datasetId: string): Promise<InvoiceListResponse> {
  if (USE_FIXTURES) {
    return fx.hasDataset(datasetId)
      ? fixture({ invoice_ids: fx.invoiceIds(datasetId) })
      : fixtureError("dataset_not_found", "This dataset has expired or does not exist.", 404)
  }
  return getJson(`/datasets/${enc(datasetId)}/documents/invoices`)
}

export function invoicePdfUrl(datasetId: string, invoiceId: string): string {
  return `${API_URL}/api/datasets/${enc(datasetId)}/documents/invoices/${enc(invoiceId)}.pdf`
}

export function exportZipUrl(datasetId: string): string {
  return `${API_URL}/api/datasets/${enc(datasetId)}/export.zip`
}

/**
 * Fetches a binary download (invoice PDF, ZIP) so errors such as
 * 501 not_implemented can be shown in the UI instead of a broken frame.
 */
export async function fetchFile(url: string): Promise<Blob> {
  if (USE_FIXTURES) {
    return fixtureError("not_implemented", "This file is not available in sample data mode yet.", 501)
  }
  const path = url.slice(`${API_URL}/api`.length)
  return (await send(path)).blob()
}

/** Message for any thrown value. */
export function errorMessage(err: unknown): string {
  if (err instanceof ApiRequestError) return err.message
  if (err instanceof Error) return err.message
  return "Something went wrong. Try again."
}

export function isApiError(err: unknown, code: string): err is ApiRequestError {
  return err instanceof ApiRequestError && err.code === code
}
