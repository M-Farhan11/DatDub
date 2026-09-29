/**
 * Fixture schemas (finance + e-commerce). Typed against src/api/types.ts so the
 * compiler checks they match the contract exactly.
 */
import type { ColumnSchema, DatasetSchema, ForeignKey, TemplateSummary } from "../types"

const col = (
  name: string,
  data_type: ColumnSchema["data_type"],
  semantic_type: ColumnSchema["semantic_type"],
  extra: Partial<ColumnSchema> = {},
): ColumnSchema => ({
  name,
  data_type,
  semantic_type,
  nullable: false,
  unique: false,
  pii: false,
  confidence: 0.9,
  allowed_values: null,
  min: null,
  max: null,
  profile: null,
  ...extra,
})

const fk = (column: string, ref_table: string, ref_column: string, min: number, max: number): ForeignKey => ({
  column,
  ref_table,
  ref_column,
  cardinality: "1:N",
  min_children: min,
  max_children: max,
  children_distribution: null,
})

export const financeSchema: DatasetSchema = {
  name: "finance_demo",
  source: "template",
  tables: [
    {
      name: "customers",
      primary_key: "customer_id",
      row_count_hint: 5000,
      columns: [
        col("customer_id", "string", "id", { unique: true, confidence: 0.99 }),
        col("full_name", "string", "person_name", { pii: true, confidence: 0.97 }),
        col("email", "string", "email", { pii: true, unique: true, confidence: 0.96 }),
        col("phone", "string", "phone", { pii: true, nullable: true, confidence: 0.88 }),
        col("country", "string", "country", {
          confidence: 0.93,
          profile: {
            null_rate: 0,
            mean: null,
            std: null,
            min: null,
            max: null,
            histogram: null,
            top_values: [
              ["United States", 0.41],
              ["Germany", 0.18],
              ["India", 0.15],
              ["United Kingdom", 0.14],
              ["Canada", 0.12],
            ],
            unique_ratio: 0.001,
          },
        }),
        col("created_at", "date", "date", { confidence: 0.95 }),
      ],
      foreign_keys: [],
    },
    {
      name: "invoices",
      primary_key: "invoice_id",
      row_count_hint: null,
      columns: [
        col("invoice_id", "string", "id", { unique: true, confidence: 0.99 }),
        col("customer_id", "string", "id", { confidence: 0.98 }),
        col("issue_date", "date", "date", { confidence: 0.94 }),
        col("due_date", "date", "date", { confidence: 0.94 }),
        col("status", "string", "status", {
          allowed_values: ["paid", "open", "overdue", "void"],
          confidence: 0.91,
          profile: {
            null_rate: 0,
            mean: null,
            std: null,
            min: null,
            max: null,
            histogram: null,
            top_values: [
              ["paid", 0.62],
              ["open", 0.21],
              ["overdue", 0.13],
              ["void", 0.04],
            ],
            unique_ratio: 0.0003,
          },
        }),
        col("total", "decimal", "currency_amount", {
          min: 0,
          confidence: 0.95,
          profile: {
            null_rate: 0,
            mean: 1284.5,
            std: 912.3,
            min: 18.4,
            max: 9860,
            histogram: [
              [0, 1000, 5120],
              [1000, 2000, 4410],
              [2000, 3000, 2630],
              [3000, 4000, 1380],
              [4000, 5000, 690],
              [5000, 6000, 320],
              [6000, 7000, 140],
              [7000, 8000, 70],
              [8000, 9000, 30],
              [9000, 10000, 10],
            ],
            top_values: null,
            unique_ratio: 0.97,
          },
        }),
      ],
      foreign_keys: [fk("customer_id", "customers", "customer_id", 0, 10)],
    },
    {
      name: "invoice_items",
      primary_key: "item_id",
      row_count_hint: null,
      columns: [
        col("item_id", "string", "id", { unique: true, confidence: 0.99 }),
        col("invoice_id", "string", "id", { confidence: 0.98 }),
        col("description", "string", "text", { confidence: 0.82 }),
        col("quantity", "integer", "quantity", { min: 1, max: 50, confidence: 0.9 }),
        col("unit_price", "decimal", "currency_amount", { min: 5, max: 2000, confidence: 0.93 }),
      ],
      foreign_keys: [fk("invoice_id", "invoices", "invoice_id", 1, 6)],
    },
    {
      name: "payments",
      primary_key: "payment_id",
      row_count_hint: null,
      columns: [
        col("payment_id", "string", "id", { unique: true, confidence: 0.99 }),
        col("invoice_id", "string", "id", { confidence: 0.98 }),
        col("paid_at", "date", "date", { confidence: 0.94 }),
        col("method", "string", "category", {
          allowed_values: ["card", "bank_transfer", "direct_debit"],
          confidence: 0.87,
        }),
        col("amount", "decimal", "currency_amount", { min: 0, confidence: 0.95 }),
      ],
      foreign_keys: [fk("invoice_id", "invoices", "invoice_id", 0, 2)],
    },
  ],
  rules: [
    {
      id: "r1",
      kind: "sum_of_children",
      table: "invoices",
      column: "total",
      params: { child_table: "invoice_items", expr: "quantity * unit_price" },
      description: "Invoice total equals the sum of its line items",
    },
    {
      id: "r2",
      kind: "date_order",
      table: "invoices",
      column: "due_date",
      params: { before: "issue_date", after: "due_date" },
      description: "An invoice is due on or after its issue date",
    },
    {
      id: "r3",
      kind: "lte_parent",
      table: "payments",
      column: "amount",
      params: { parent_table: "invoices", parent_column: "total" },
      description: "A payment never exceeds its invoice total",
    },
  ],
  document_hints: {
    invoice: { header_table: "invoices", items_table: "invoice_items", party_table: "customers" },
  },
}

export const ecommerceSchema: DatasetSchema = {
  name: "ecommerce_demo",
  source: "template",
  tables: [
    {
      name: "customers",
      primary_key: "customer_id",
      row_count_hint: 2000,
      columns: [
        col("customer_id", "string", "id", { unique: true, confidence: 0.99 }),
        col("full_name", "string", "person_name", { pii: true, confidence: 0.97 }),
        col("email", "string", "email", { pii: true, unique: true, confidence: 0.96 }),
        col("city", "string", "city", { confidence: 0.9 }),
      ],
      foreign_keys: [],
    },
    {
      name: "orders",
      primary_key: "order_id",
      row_count_hint: null,
      columns: [
        col("order_id", "string", "id", { unique: true, confidence: 0.99 }),
        col("customer_id", "string", "id", { confidence: 0.98 }),
        col("created_at", "date", "date", { confidence: 0.94 }),
        col("status", "string", "status", {
          allowed_values: ["placed", "shipped", "delivered", "returned"],
          confidence: 0.9,
        }),
        col("total", "decimal", "currency_amount", { min: 0, confidence: 0.95 }),
      ],
      foreign_keys: [fk("customer_id", "customers", "customer_id", 0, 12)],
    },
    {
      name: "order_items",
      primary_key: "order_item_id",
      row_count_hint: null,
      columns: [
        col("order_item_id", "string", "id", { unique: true, confidence: 0.99 }),
        col("order_id", "string", "id", { confidence: 0.98 }),
        col("sku", "string", "sku", { confidence: 0.92 }),
        col("quantity", "integer", "quantity", { min: 1, max: 20, confidence: 0.9 }),
        col("unit_price", "decimal", "currency_amount", { min: 1, max: 900, confidence: 0.93 }),
      ],
      foreign_keys: [fk("order_id", "orders", "order_id", 1, 8)],
    },
    {
      name: "payments",
      primary_key: "payment_id",
      row_count_hint: null,
      columns: [
        col("payment_id", "string", "id", { unique: true, confidence: 0.99 }),
        col("order_id", "string", "id", { confidence: 0.98 }),
        col("paid_at", "date", "date", { confidence: 0.94 }),
        col("amount", "decimal", "currency_amount", { min: 0, confidence: 0.95 }),
      ],
      foreign_keys: [fk("order_id", "orders", "order_id", 0, 1)],
    },
  ],
  rules: [
    {
      id: "r1",
      kind: "sum_of_children",
      table: "orders",
      column: "total",
      params: { child_table: "order_items", expr: "quantity * unit_price" },
      description: "Order total equals the sum of its items",
    },
    {
      id: "r2",
      kind: "lte_parent",
      table: "payments",
      column: "amount",
      params: { parent_table: "orders", parent_column: "total" },
      description: "A payment never exceeds its order total",
    },
  ],
  document_hints: null,
}

export const templates: TemplateSummary[] = [
  {
    id: "finance",
    name: "Finance",
    description: "Customers, invoices, line items and payments. Totals reconcile and invoices render as PDFs.",
    tables: 4,
  },
  {
    id: "ecommerce",
    name: "E-commerce",
    description: "Customers, orders, order items and payments with order totals that add up.",
    tables: 4,
  },
]

export const templateSchemas: Record<string, DatasetSchema> = {
  finance: financeSchema,
  ecommerce: ecommerceSchema,
}
