import type { DatasetSchema, ForeignKey } from "@/api/types"

export const MAX_ROWS_PER_TABLE = 100_000
export const MAX_TOTAL_CELLS = 8_000_000

/** Average children per parent: from the sample distribution when present, else the min/max midpoint. */
function averageChildren(fk: ForeignKey): number {
  if (fk.children_distribution && fk.children_distribution.length > 0) {
    const total = fk.children_distribution.reduce((s, [, f]) => s + f, 0) || 1
    return fk.children_distribution.reduce((s, [n, f]) => s + n * f, 0) / total
  }
  return (fk.min_children + fk.max_children) / 2
}

/**
 * Rough row count per table: root tables use the requested rows, children
 * follow their first foreign key's cardinality. The backend decides the
 * exact numbers; this is only for hints and warnings.
 */
export function estimateRows(schema: DatasetSchema, rootRows: Record<string, number>): Map<string, number> {
  const byName = new Map(schema.tables.map((t) => [t.name, t]))
  const memo = new Map<string, number>()
  const visit = (name: string, trail: Set<string>): number => {
    const known = memo.get(name)
    if (known !== undefined) return known
    const table = byName.get(name)
    if (!table || trail.has(name)) return 0
    trail.add(name)
    let n: number
    const fk = table.foreign_keys.find((f) => f.ref_table !== name && byName.has(f.ref_table))
    if (!fk) n = rootRows[name] ?? table.row_count_hint ?? 100
    else n = Math.round(visit(fk.ref_table, trail) * averageChildren(fk))
    trail.delete(name)
    memo.set(name, n)
    return n
  }
  for (const t of schema.tables) visit(t.name, new Set())
  return memo
}

export function estimateCells(schema: DatasetSchema, rows: Map<string, number>): number {
  return schema.tables.reduce((sum, t) => sum + (rows.get(t.name) ?? 0) * t.columns.length, 0)
}

export function rowsError(n: number | undefined): string | null {
  if (n === undefined || !Number.isInteger(n) || n < 1) return "Enter at least 1 row."
  return null
}
