import { cn } from "@/lib/utils"

export interface PreviewColumn {
  name: string
  type: string
  pk?: boolean
  pii?: boolean
  /** Referenced table name for a foreign key column. */
  fk?: string
}

interface PreviewTableProps {
  name: string
  rows: string
  columns: PreviewColumn[]
  /** Optional footer note, e.g. an expected anomaly. */
  anomaly?: string
  cardRef?: (el: HTMLDivElement | null) => void
  /** Called for each foreign-key row so connector lines can target it. */
  fkRowRef?: (column: string, el: HTMLDivElement | null) => void
  className?: string
}

export function PreviewTable({ name, rows, columns, anomaly, cardRef, fkRowRef, className }: PreviewTableProps) {
  return (
    <div ref={cardRef} className={cn("w-full overflow-hidden rounded-xl bg-card shadow-md", className)}>
      <div className="flex items-center justify-between bg-surface-low px-4 py-2">
        <span className="font-heading text-headline-sm text-ink">{name}</span>
        <span className="tabular font-mono text-code-sm text-hint">{rows} rows</span>
      </div>
      <div className="space-y-1 p-2 font-mono text-code-sm text-ink">
        {columns.map((col) => (
          <div
            key={col.name}
            ref={col.fk ? (el) => fkRowRef?.(col.name, el) : undefined}
            className={cn(
              "flex items-center justify-between gap-2 rounded px-1 py-1",
              col.fk ? "bg-surface-low/70" : "hover:bg-surface-low"
            )}
          >
            <span className="flex min-w-0 items-center gap-1.5">
              <span
                className={cn(
                  "truncate",
                  col.pk && "font-medium text-primary-deep",
                  col.fk && "font-medium text-primary"
                )}
              >
                {col.name}
              </span>
              {col.pii && (
                <span className="rounded-full bg-primary-tint px-1.5 font-heading text-[10px] font-semibold tracking-wider text-primary-deep">
                  PII
                </span>
              )}
            </span>
            {col.pk ? (
              <span className="font-heading text-[11px] font-semibold text-hint">PK</span>
            ) : col.fk ? (
              <span className="shrink-0 font-heading text-[11px] font-semibold text-primary-deep">FK → {col.fk}</span>
            ) : (
              <span className="shrink-0 text-hint">{col.type}</span>
            )}
          </div>
        ))}
      </div>
      {anomaly && (
        <div className="m-2 flex items-center gap-2 rounded-lg bg-surface-highest/60 p-2.5 font-mono text-code-sm text-expected">
          <span className="size-2 shrink-0 rounded-full bg-coral" aria-hidden="true" />
          <span className="truncate">{anomaly}</span>
        </div>
      )}
    </div>
  )
}
