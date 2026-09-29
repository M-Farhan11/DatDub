/**
 * Fixture versions of POST /api/generate and GET /api/datasets/{id}/tables/{t}.
 * Row counts follow the requested root rows; ground truth and the report follow
 * the selected scenarios, mirroring the backend's behaviour described in
 * docs/api-contract.md.
 */
import type {
  GenerateRequest,
  GenerateResponse,
  GroundTruthEntry,
  TablePage,
  ValidationCheck,
} from "../types"
import { SCENARIO_IDS, idFor, rowFor, type RowContext } from "./rows"

interface FixtureDataset {
  counts: Record<string, number>
  ctx: RowContext
}

const datasets = new Map<string, FixtureDataset>()

const fmt = (n: number) => n.toLocaleString("en-US")

/** Stand-in IDs for proposals that have no preset list (e.g. from the real AI). */
function affectedIdsFor(scenarioId: string, table: string, count: number): string[] {
  const preset = SCENARIO_IDS[scenarioId]
  if (preset) {
    if (count <= preset.length) return preset.slice(0, count)
    const extra = Array.from({ length: count - preset.length }, (_, k) => idFor(table, 400 + k * 7))
    return [...preset, ...extra]
  }
  return Array.from({ length: count }, (_, k) => idFor(table, 300 + k * 11))
}

export function generate(req: GenerateRequest): GenerateResponse {
  const customers = Math.max(1, req.rows.customers ?? req.schema.tables[0]?.row_count_hint ?? 100)
  const invoices = Math.round(customers * 2.96)
  const duplicates = req.scenarios
    .filter((s) => s.proposal.kind === "duplicate_record")
    .reduce((n, s) => n + s.count, 0)
  const counts: Record<string, number> = {
    customers,
    invoices,
    invoice_items: invoices * 3,
    payments: Math.round(invoices * 0.84) + duplicates,
  }

  const ground_truth: GroundTruthEntry[] = req.scenarios.map(({ proposal, count }) => ({
    scenario_id: proposal.id,
    kind: proposal.kind,
    table: proposal.table,
    affected_ids: affectedIdsFor(proposal.id, proposal.table, count),
    description: proposal.description,
    expected_behavior: proposal.expected_behavior,
  }))

  const affected = new Map<string, string>()
  for (const entry of ground_truth) for (const id of entry.affected_ids) affected.set(id, entry.scenario_id)

  const dataset_id = `ds_${(req.seed >>> 0).toString(16).padStart(4, "0")}${customers.toString(36)}`
  const ctx: RowContext = { seed: req.seed, customers, affected }
  datasets.set(dataset_id, { counts, ctx })

  const tables = req.schema.tables.map((t) => t.name).filter((name) => name in counts)
  const previews = Object.fromEntries(
    tables.map((t) => [t, Array.from({ length: Math.min(50, counts[t]) }, (_, i) => rowFor(t, i, ctx))]),
  )

  const expectedFor = (ruleId: string, table: string) =>
    ground_truth
      .filter((g) => g.table === table && req.scenarios.some((s) => s.proposal.id === g.scenario_id && s.proposal.rule_id === ruleId))
      .reduce((n, g) => n + g.affected_ids.length, 0)

  const checks: ValidationCheck[] = []
  for (const table of req.schema.tables.filter((t) => t.name in counts)) {
    const n = counts[table.name]
    checks.push({ name: "PK uniqueness", table: table.name, status: "PASS", score: 1, detail: `${fmt(n)}/${fmt(n)} unique`, expected_violations: 0 })
    for (const fk of table.foreign_keys) {
      checks.push({
        name: `FK integrity (${fk.column} → ${fk.ref_table})`,
        table: table.name,
        status: "PASS",
        score: 1,
        detail: `${fmt(n)}/${fmt(n)} resolve`,
        expected_violations: 0,
      })
    }
    checks.push({ name: "Types & nullability", table: table.name, status: "PASS", score: 1, detail: `${fmt(n)}/${fmt(n)} rows valid`, expected_violations: 0 })
  }
  for (const rule of req.schema.rules) {
    const n = counts[rule.table] ?? 0
    const expected = expectedFor(rule.id, rule.table)
    checks.push({
      name: `Rule ${rule.id}: ${rule.description}`,
      table: rule.table,
      status: "PASS",
      score: 1,
      detail: expected > 0 ? `${fmt(n - expected)}/${fmt(n)} pass, ${expected} injected (expected)` : `${fmt(n)}/${fmt(n)} pass`,
      expected_violations: expected,
    })
  }

  return {
    dataset_id,
    row_counts: Object.fromEntries(tables.map((t) => [t, counts[t]])),
    previews,
    report: {
      overall: "PASS",
      checks,
      similarity: {
        overall: 0.91,
        per_column: {
          "customers.country": 0.95,
          "invoices.status": 0.93,
          "invoices.total": 0.88,
        },
      },
    },
    ground_truth,
  }
}

export function tablePage(datasetId: string, table: string, offset: number, limit: number): TablePage | null {
  const ds = datasets.get(datasetId)
  if (!ds || !(table in ds.counts)) return null
  const total = ds.counts[table]
  const end = Math.min(total, offset + limit)
  const rows = Array.from({ length: Math.max(0, end - offset) }, (_, k) => rowFor(table, offset + k, ds.ctx))
  return { table, total, rows }
}

export function hasDataset(datasetId: string): boolean {
  return datasets.has(datasetId)
}

export function invoiceIds(datasetId: string): string[] {
  const n = Math.min(20, datasets.get(datasetId)?.counts.invoices ?? 20)
  return Array.from({ length: n }, (_, i) => idFor("invoices", i))
}
