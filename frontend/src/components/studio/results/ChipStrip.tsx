import type { ReactNode } from "react"
import { MonoText } from "@/components/shared/MonoText"
import { cn } from "@/lib/utils"

export interface ChipItem {
  id: string
  label: string
  /** Small secondary text, e.g. a row count. */
  meta?: string
}

interface ChipStripProps {
  label: string
  items: ChipItem[]
  value: string | null
  onChange: (id: string) => void
  /** Optional control on the left of the strip, e.g. a search box. */
  lead?: ReactNode
  /** Optional note on the right, e.g. "Showing 100 of 886". */
  trail?: ReactNode
}

/**
 * Full-width card with the choices side by side (tables, invoices). The
 * selected chip is filled in the brand blue so it stands apart at a glance.
 * Scrolls sideways when there are more chips than fit.
 */
export function ChipStrip({ label, items, value, onChange, lead, trail }: ChipStripProps) {
  return (
    <nav
      aria-label={label}
      className="flex flex-col gap-3 rounded-2xl border border-line bg-card p-3 shadow-sm md:flex-row md:items-center"
    >
      {lead && <div className="shrink-0 md:w-56">{lead}</div>}
      <ul className="flex min-w-0 flex-1 gap-2 overflow-x-auto pb-1 [scrollbar-width:thin] md:pb-0">
        {items.map((item) => {
          const active = item.id === value
          return (
            <li key={item.id} className="shrink-0">
              <button
                type="button"
                onClick={() => onChange(item.id)}
                aria-current={active ? "true" : undefined}
                className={cn(
                  "flex h-10 items-center gap-2.5 rounded-xl border px-4 transition-colors",
                  active
                    ? "border-primary bg-primary text-primary-foreground shadow-sm shadow-primary/20"
                    : "border-line bg-surface-low text-ink hover:border-primary/50 hover:bg-primary-tint/40",
                )}
              >
                <MonoText className="font-medium">{item.label}</MonoText>
                {item.meta && (
                  <span
                    className={cn(
                      "tabular rounded-md px-1.5 py-0.5 font-mono text-code-sm",
                      active ? "bg-white/20 text-primary-foreground" : "bg-card text-ink-muted",
                    )}
                  >
                    {item.meta}
                  </span>
                )}
              </button>
            </li>
          )
        })}
      </ul>
      {trail && <div className="shrink-0 text-body-sm text-hint">{trail}</div>}
    </nav>
  )
}
