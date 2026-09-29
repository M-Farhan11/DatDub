import type { Rule } from "@/api/types"

const words = (name: unknown) => String(name ?? "").replace(/_/g, " ")

const str = (v: unknown): string | null => (typeof v === "string" && v.trim() ? v : null)

/**
 * A readable sentence for a rule. Uses the rule's own description when it has
 * one; otherwise builds one from the kind and params (AI-drafted schemas can
 * arrive with an empty description).
 */
export function describeRule(rule: Rule): string {
  if (rule.description.trim()) return rule.description
  const p = rule.params
  const col = words(rule.column)
  const table = words(rule.table)
  switch (rule.kind) {
    case "range":
      return `${col} in ${table} is between ${words(p.min)} and ${words(p.max)}`
    case "allowed_values": {
      const values = Array.isArray(p.values) ? p.values.map(String) : []
      return values.length ? `${col} in ${table} is one of: ${values.join(", ")}` : `${col} in ${table} uses a fixed list of values`
    }
    case "date_order": {
      const before = words(str(p.before) ?? "the earlier date")
      const after = words(str(p.after) ?? rule.column)
      const via = str(p.via_fk)
      return via ? `${after} is on or after the linked ${before} (through ${words(via)})` : `${after} is on or after ${before}`
    }
    case "sum_of_children": {
      const child = words(str(p.child_table) ?? "its items")
      const expr = words(str(p.expr) ?? "their amounts")
      return `${table} ${col} equals the sum of ${expr} over its ${child}`
    }
    case "lte_parent":
      return `${table} ${col} is never more than ${words(p.parent_table)} ${words(p.parent_column)}`
  }
}

/** Backend check names look like "Rule r1: <description>"; fill in a missing description. */
export function describeCheckName(name: string, rules: Rule[]): string {
  const match = /^Rule (\S+?):\s*$/.exec(name)
  if (!match) return name
  const rule = rules.find((r) => r.id === match[1])
  return rule ? `Rule ${rule.id}: ${describeRule(rule)}` : name
}
