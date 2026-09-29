/** Fixture responses for the source endpoints (prompt, CSV, database, SQLite). */
import type { DbTablesResponse, FromDbResponse, SchemaResponse } from "../types"
import { financeSchema } from "./schemas"

export const promptResponse: SchemaResponse = {
  schema: { ...financeSchema, name: "billing_system", source: "prompt" },
  notes: [
    "Assumed each invoice can have several payments (1:N).",
    "Marked full_name, email and phone as personal data.",
  ],
}

export const csvResponse: SchemaResponse = {
  schema: { ...financeSchema, name: "uploaded_files", source: "csv" },
  notes: ["Linked invoice_items.csv to invoices.csv through the invoice_id column."],
}

export const dbTablesResponse: DbTablesResponse = {
  tables: [
    { name: "customers", schema: "public", column_count: 6, estimated_rows: 4820, references: [] },
    { name: "invoices", schema: "public", column_count: 6, estimated_rows: 14210, references: ["customers"] },
    { name: "invoice_items", schema: "public", column_count: 5, estimated_rows: 43900, references: ["invoices"] },
    { name: "payments", schema: "public", column_count: 5, estimated_rows: 12050, references: ["invoices"] },
    { name: "audit_log", schema: "public", column_count: 8, estimated_rows: 310400, references: [] },
  ],
}

export const fromDbResponse: FromDbResponse = {
  schema: { ...financeSchema, name: "billing", source: "postgres" },
  auto_added: ["customers"],
  rows_sampled: 800,
  notes: ["Sampled 200 rows per table in a read-only transaction. The rows were discarded after profiling."],
}

export const fromSqliteResponse: FromDbResponse = {
  ...fromDbResponse,
  schema: { ...financeSchema, name: "billing_sqlite", source: "sqlite" },
}
