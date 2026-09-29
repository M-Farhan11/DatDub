/**
 * Deterministic finance rows for fixtures mode. Row i of a table is always the
 * same, so previews and paging agree. Rows touched by selected scenarios are
 * altered so the ground truth points at visibly unusual data.
 */
import type { Row } from "../types"

const FIRST = ["Elena", "Marcus", "Priya", "Tomas", "Aiko", "Jonah", "Fatima", "Lars", "Chloe", "Omar", "Grace", "Mateo"]
const LAST = ["Rostova", "Vance", "Iyer", "Alvarez", "Tanaka", "Reed", "Haddad", "Nilsson", "Martin", "Kaya", "Okafor", "Silva"]
const COUNTRY = ["United States", "United States", "Germany", "India", "United Kingdom", "Canada"]
const ITEMS = ["Platform licence", "Support plan", "Onboarding", "Data connector", "Extra seats", "Storage add-on"]
const STATUS = ["paid", "paid", "paid", "open", "overdue", "void"]
const METHOD = ["card", "bank_transfer", "direct_debit"]

/** Affected IDs per fixture scenario (first ones sit on the first preview page). */
export const SCENARIO_IDS: Record<string, string[]> = {
  s1: ["PAY-0012", "PAY-0027", "PAY-0102", "PAY-0103", "PAY-0140", "PAY-0188", "PAY-0215", "PAY-0260"],
  s2: ["PAY-0021", "PAY-0034", "PAY-0048", "PAY-0077", "PAY-0091"],
  s3: ["INV-00005", "INV-00013", "INV-00031", "INV-00046", "INV-00058", "INV-00064"],
  s4: [
    "CUS-00007", "CUS-00019", "CUS-00042", "CUS-00046", "CUS-00061", "CUS-00083", "CUS-00097", "CUS-00104",
    "CUS-00118", "CUS-00131", "CUS-00142", "CUS-00157", "CUS-00163", "CUS-00178", "CUS-00190", "CUS-00204",
    "CUS-00219", "CUS-00233", "CUS-00247", "CUS-00251", "CUS-00266", "CUS-00279", "CUS-00284", "CUS-00296",
    "CUS-00301",
  ],
  s5: ["INV-00009", "INV-00027", "INV-00088"],
}

function rand(seed: number): number {
  let x = Math.imul(seed ^ 0x9e3779b9, 0x85ebca6b)
  x = Math.imul(x ^ (x >>> 13), 0xc2b2ae35)
  return ((x ^ (x >>> 16)) >>> 0) / 4294967296
}
const pick = <T,>(arr: T[], s: number): T => arr[Math.floor(rand(s) * arr.length)]
const pad = (n: number, width: number) => String(n).padStart(width, "0")
const money = (n: number) => Math.round(n * 100) / 100
const day = (offset: number) => new Date(Date.UTC(2025, 0, 1) + offset * 86_400_000).toISOString().slice(0, 10)

export const idFor = (table: string, i: number): string => {
  switch (table) {
    case "customers":
      return `CUS-${pad(i + 1, 5)}`
    case "invoices":
      return `INV-${pad(i + 1, 5)}`
    case "invoice_items":
      return `ITM-${pad(i + 1, 6)}`
    default:
      return `PAY-${pad(i + 1, 4)}`
  }
}

export interface RowContext {
  seed: number
  customers: number
  /** affected id -> scenario id, only for selected scenarios */
  affected: Map<string, string>
}

export function rowFor(table: string, i: number, ctx: RowContext): Row {
  const s = ctx.seed * 7919 + i * 31
  const id = idFor(table, i)
  const scenario = ctx.affected.get(id)

  switch (table) {
    case "customers": {
      const first = pick(FIRST, s)
      const last = pick(LAST, s + 1)
      return {
        customer_id: id,
        full_name: `${first} ${last}`,
        email: `${first}.${last}${i + 1}@example.com`.toLowerCase(),
        phone: scenario === "s4" ? null : `+1 555 01${pad(Math.floor(rand(s + 2) * 100), 2)} ${pad(i % 10000, 4)}`,
        country: pick(COUNTRY, s + 3),
        created_at: day(Math.floor(rand(s + 4) * 300)),
      }
    }
    case "invoices": {
      const issue = Math.floor(rand(s) * 330)
      const customer = Math.floor(rand(s + 1) * ctx.customers)
      return {
        invoice_id: id,
        customer_id: idFor("customers", customer),
        issue_date: day(issue),
        due_date: scenario === "s3" ? "2028-02-29" : day(issue + 30),
        status: pick(STATUS, s + 2),
        total: scenario === "s5" ? 98_500 : money(rand(s + 3) * 4800 + 120),
      }
    }
    case "invoice_items":
      return {
        item_id: id,
        invoice_id: idFor("invoices", Math.floor(i / 3)),
        description: pick(ITEMS, s),
        quantity: 1 + Math.floor(rand(s + 1) * 6),
        unit_price: money(rand(s + 2) * 1800 + 25),
      }
    default: {
      const amount = money(rand(s + 2) * 4800 + 120)
      return {
        payment_id: id,
        invoice_id: idFor("invoices", Math.floor(i / 1.2)),
        paid_at: day(Math.floor(rand(s) * 340)),
        method: pick(METHOD, s + 1),
        amount: scenario === "s1" ? money(amount + 40) : amount,
      }
    }
  }
}
