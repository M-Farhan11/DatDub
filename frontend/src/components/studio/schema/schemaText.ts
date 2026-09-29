import type { ForeignKey, RuleKind, SemanticType } from "@/api/types"

const words = (name: string) => name.replace(/_/g, " ")

/** Naive singular for table names: "invoices" -> "invoice", "categories" -> "category". */
export function singular(name: string): string {
  const w = words(name)
  if (w.endsWith("ies")) return `${w.slice(0, -3)}y`
  if (w.endsWith("sses")) return w.slice(0, -2)
  if (w.endsWith("s") && !w.endsWith("ss")) return w.slice(0, -1)
  return w
}

export const plural = (name: string) => words(name)

/** Plain-words edge label, e.g. "1 customer has 0 to 10 invoices". */
export function relationLabel(fk: ForeignKey, childTable: string): string {
  const parent = singular(fk.ref_table)
  if (fk.cardinality === "1:1") return `1 ${parent} has 1 ${singular(childTable)}`
  const count = fk.min_children === fk.max_children ? `${fk.max_children}` : `${fk.min_children} to ${fk.max_children}`
  const child = fk.max_children === 1 ? singular(childTable) : plural(childTable)
  return `1 ${parent} has ${count} ${child}`
}

export const RULE_KIND_LABEL: Record<RuleKind, string> = {
  range: "Range",
  allowed_values: "Allowed values",
  date_order: "Date order",
  sum_of_children: "Total",
  lte_parent: "Limit",
}

export const SEMANTIC_TYPES = [
  "id", "person_name", "first_name", "last_name", "email", "phone", "address", "city", "country",
  "company", "date", "datetime", "currency_amount", "quantity", "percentage", "category", "status",
  "text", "url", "sku", "iban", "generic_number", "generic_string",
] as const satisfies readonly SemanticType[]
