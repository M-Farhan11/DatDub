import type { DatasetSchema, TableSchema } from "@/api/types"

export const NODE_WIDTH = 280
const COLUMN_GAP = 120
const ROW_GAP = 40
const HEADER_HEIGHT = 48
const ROW_HEIGHT = 32

export const estimateHeight = (table: TableSchema) => HEADER_HEIGHT + table.columns.length * ROW_HEIGHT + 12

/** FK depth: 0 for tables without foreign keys, else 1 + deepest parent. Cycles are cut. */
function depths(schema: DatasetSchema): Map<string, number> {
  const byName = new Map(schema.tables.map((t) => [t.name, t]))
  const memo = new Map<string, number>()
  const visit = (name: string, trail: Set<string>): number => {
    const known = memo.get(name)
    if (known !== undefined) return known
    const table = byName.get(name)
    if (!table || trail.has(name)) return 0
    trail.add(name)
    let depth = 0
    for (const fk of table.foreign_keys) {
      if (fk.ref_table !== name && byName.has(fk.ref_table)) depth = Math.max(depth, visit(fk.ref_table, trail) + 1)
    }
    trail.delete(name)
    memo.set(name, depth)
    return depth
  }
  for (const t of schema.tables) visit(t.name, new Set())
  return memo
}

/** Left-to-right positions by FK depth; each column is centred vertically on the tallest. */
export function layoutTables(schema: DatasetSchema): Map<string, { x: number; y: number }> {
  const depthOf = depths(schema)
  const columns = new Map<number, TableSchema[]>()
  for (const t of schema.tables) {
    const d = depthOf.get(t.name) ?? 0
    columns.set(d, [...(columns.get(d) ?? []), t])
  }
  const heightOf = (tables: TableSchema[]) =>
    tables.reduce((h, t) => h + estimateHeight(t), 0) + ROW_GAP * Math.max(0, tables.length - 1)
  const tallest = Math.max(0, ...[...columns.values()].map(heightOf))

  const positions = new Map<string, { x: number; y: number }>()
  for (const [depth, tables] of columns) {
    let y = (tallest - heightOf(tables)) / 2
    for (const t of tables) {
      positions.set(t.name, { x: depth * (NODE_WIDTH + COLUMN_GAP), y })
      y += estimateHeight(t) + ROW_GAP
    }
  }
  return positions
}

/** Changes only when tables or links change, not when a column's details are edited. */
export const structureKey = (schema: DatasetSchema) =>
  schema.tables
    .map((t) => `${t.name}(${t.columns.map((c) => c.name).join(",")})[${t.foreign_keys.map((f) => `${f.column}>${f.ref_table}`).join(",")}]`)
    .join("|")
