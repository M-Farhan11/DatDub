import type { DbTableInfo } from "@/api/types"

/**
 * Tables the chosen ones depend on (FK parents, recursively) that were not
 * chosen themselves. The backend auto-adds the same set.
 */
export function requiredParents(tables: DbTableInfo[], chosen: Set<string>): Map<string, string> {
  const byName = new Map(tables.map((t) => [t.name, t]))
  /** parent -> first child that needs it */
  const needed = new Map<string, string>()
  const stack = [...chosen]
  while (stack.length) {
    const name = stack.pop() as string
    for (const parent of byName.get(name)?.references ?? []) {
      if (parent === name || chosen.has(parent) || needed.has(parent)) continue
      needed.set(parent, name)
      stack.push(parent)
    }
  }
  return needed
}

/** Default choice: every table that references another, so parents show as auto-added. */
export function defaultChoice(tables: DbTableInfo[]): Set<string> {
  const withRefs = tables.filter((t) => t.references.length > 0).map((t) => t.name)
  return new Set(withRefs.length > 0 ? withRefs : tables.slice(0, 1).map((t) => t.name))
}
