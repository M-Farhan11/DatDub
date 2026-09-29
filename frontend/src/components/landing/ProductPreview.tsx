import { useCallback, useLayoutEffect, useRef, useState } from "react"
import { FolderOpen, Network, Table } from "lucide-react"
import { PreviewTable, type PreviewColumn } from "./PreviewTable"

interface TableSpec {
  name: string
  rows: string
  columns: PreviewColumn[]
  anomaly?: string
}

const customers: TableSpec = {
  name: "customers",
  rows: "5,000",
  columns: [
    { name: "id", type: "uuid", pk: true },
    { name: "name", type: "varchar" },
    { name: "email", type: "varchar", pii: true },
    { name: "created_at", type: "timestamp" },
  ],
}

const invoices: TableSpec = {
  name: "invoices",
  rows: "1,240",
  columns: [
    { name: "id", type: "uuid", pk: true },
    { name: "customer_id", type: "uuid", fk: "customers" },
    { name: "amount", type: "numeric" },
    { name: "due_date", type: "date" },
    { name: "status", type: "varchar" },
  ],
}

const invoiceItems: TableSpec = {
  name: "invoice_items",
  rows: "3,800",
  columns: [
    { name: "id", type: "uuid", pk: true },
    { name: "invoice_id", type: "uuid", fk: "invoices" },
    { name: "quantity", type: "integer" },
    { name: "unit_price", type: "numeric" },
  ],
}

const payments: TableSpec = {
  name: "payments",
  rows: "1,190",
  columns: [
    { name: "id", type: "uuid", pk: true },
    { name: "invoice_id", type: "uuid", fk: "invoices" },
    { name: "amount", type: "numeric" },
    { name: "method", type: "varchar" },
  ],
  anomaly: "expected anomaly: overpayment +$40",
}

/** Connector: parent card -> child's foreign-key row. */
const LINKS = [
  { from: "customers", to: "invoices.customer_id" },
  { from: "invoices", to: "invoice_items.invoice_id" },
  { from: "invoices", to: "payments.invoice_id" },
]

const STEPS = ["Source", "Schema", "Configure", "Results", "Export"]

export function ProductPreview() {
  const canvasRef = useRef<HTMLDivElement>(null)
  const cards = useRef(new Map<string, HTMLElement>())
  const fkRows = useRef(new Map<string, HTMLElement>())
  const [paths, setPaths] = useState<string[]>([])

  const cardRef = (table: string) => (el: HTMLDivElement | null) => {
    if (el) cards.current.set(table, el)
    else cards.current.delete(table)
  }
  const fkRowRef = (table: string) => (column: string, el: HTMLDivElement | null) => {
    const key = `${table}.${column}`
    if (el) fkRows.current.set(key, el)
    else fkRows.current.delete(key)
  }

  const measure = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const origin = canvas.getBoundingClientRect()
    const next: string[] = []
    for (const link of LINKS) {
      const source = cards.current.get(link.from)?.getBoundingClientRect()
      const target = fkRows.current.get(link.to)?.getBoundingClientRect()
      // Only draw when the child sits to the right of the parent (wide layouts).
      if (!source || !target || target.left <= source.right + 8) continue
      const sx = source.right - origin.left
      const sy = source.top - origin.top + 58
      const ex = target.left - origin.left - 4
      const ey = target.top - origin.top + target.height / 2
      const dx = (ex - sx) / 2
      next.push(`M ${sx} ${sy} C ${sx + dx} ${sy}, ${ex - dx} ${ey}, ${ex} ${ey}`)
    }
    setPaths(next)
  }, [])

  useLayoutEffect(() => {
    measure()
    const observer = new ResizeObserver(measure)
    if (canvasRef.current) observer.observe(canvasRef.current)
    return () => observer.disconnect()
  }, [measure])

  return (
    <section aria-label="Product preview" className="w-full pb-20 md:pb-28">
      <div className="mx-auto max-w-[1160px] px-margin md:px-margin-lg">
        <figure className="w-full overflow-hidden rounded-xl bg-card shadow-xl">
          <figcaption className="sr-only">
            The DatDub studio showing a finance schema with four connected tables and an injected edge case.
          </figcaption>

          {/* window chrome */}
          <div className="flex flex-wrap items-center justify-between gap-2 bg-surface-low px-4 py-2 md:px-6">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5" aria-hidden="true">
                <span className="size-3 rounded-full bg-line" />
                <span className="size-3 rounded-full bg-line" />
                <span className="size-3 rounded-full bg-line" />
              </div>
              <span className="font-mono text-code-md text-ink-muted">
                finance_demo <span className="text-hint">·</span> seed 42
              </span>
            </div>
            <ol className="hidden items-center gap-2 lg:flex" aria-label="Workflow steps">
              {STEPS.map((step, i) =>
                step === "Schema" ? (
                  <li
                    key={step}
                    aria-current="step"
                    className="flex items-center gap-1.5 rounded-full bg-primary-tint px-3 py-1 font-heading text-label-md font-medium text-primary-deep"
                  >
                    <span className="size-2 rounded-full bg-primary-deep" aria-hidden="true" />
                    {i + 1} {step}
                  </li>
                ) : (
                  <li key={step} className="px-2 py-0.5 font-heading text-label-md font-medium text-hint">
                    {i + 1} {step}
                  </li>
                )
              )}
            </ol>
            <span className="flex items-center gap-1.5 rounded-full bg-pass/10 px-3 py-1 font-mono text-code-sm font-medium text-pass">
              <span className="size-2 rounded-full bg-pass" aria-hidden="true" />
              Integrity: 100% pass
            </span>
          </div>

          {/* workspace */}
          <div className="relative flex min-h-[580px] flex-col bg-canvas md:flex-row">
            <div
              className="flex shrink-0 items-center gap-2 bg-card px-2 py-2 md:w-14 md:flex-col md:py-4"
              aria-hidden="true"
            >
              <span className="flex size-10 items-center justify-center rounded-lg bg-primary-tint text-primary-deep">
                <Network className="size-5" />
              </span>
              <span className="flex size-10 items-center justify-center rounded-lg text-hint">
                <Table className="size-5" />
              </span>
              <span className="flex size-10 items-center justify-center rounded-lg text-hint">
                <FolderOpen className="size-5" />
              </span>
            </div>

            <div ref={canvasRef} className="relative flex-1 overflow-x-auto p-4 md:p-6">
              <svg className="pointer-events-none absolute inset-0 z-0 size-full" aria-hidden="true">
                <defs>
                  <marker id="preview-dot" markerWidth="6" markerHeight="6" refX="3" refY="3">
                    <circle cx="3" cy="3" r="2.5" fill="var(--primary)" />
                  </marker>
                </defs>
                {paths.map((d) => (
                  <path
                    key={d}
                    d={d}
                    fill="none"
                    stroke="var(--primary)"
                    strokeWidth="1.5"
                    strokeDasharray="4 3"
                    opacity="0.8"
                    markerEnd="url(#preview-dot)"
                  />
                ))}
              </svg>

              <div className="relative z-10 grid grid-cols-1 items-start gap-6 md:grid-cols-2 lg:grid-cols-3 lg:gap-16">
                <PreviewTable {...customers} cardRef={cardRef("customers")} className="max-w-[280px]" />
                <PreviewTable
                  {...invoices}
                  cardRef={cardRef("invoices")}
                  fkRowRef={fkRowRef("invoices")}
                  className="max-w-[280px]"
                />
                <div className="w-full max-w-[290px] space-y-4">
                  <PreviewTable {...invoiceItems} fkRowRef={fkRowRef("invoice_items")} />
                  <PreviewTable {...payments} fkRowRef={fkRowRef("payments")} />
                </div>
              </div>
            </div>
          </div>

          {/* status bar */}
          <div className="flex flex-wrap items-center justify-between gap-2 bg-surface-low px-4 py-2.5 font-mono text-code-sm text-ink-muted md:px-6">
            <span>
              4 tables <span className="text-hint">·</span> 0 orphan records
            </span>
            <span className="flex items-center gap-1.5 font-medium text-pass">
              <span className="size-2 rounded-full bg-pass" aria-hidden="true" />
              Referential integrity: 100% pass
            </span>
          </div>
        </figure>
      </div>
    </section>
  )
}
