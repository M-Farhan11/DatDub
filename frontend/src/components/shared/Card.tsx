import type { ComponentProps, ReactNode } from "react"
import { cn } from "@/lib/utils"

interface CardProps extends ComponentProps<"section"> {
  title?: string
  description?: ReactNode
  actions?: ReactNode
  /** Remove the inner padding (e.g. for tables that run edge to edge). */
  flush?: boolean
}

/** White panel with the 12px card radius used across the studio. */
export function Card({ title, description, actions, flush, className, children, ...rest }: CardProps) {
  return (
    <section className={cn("rounded-xl border border-line bg-card shadow-sm", className)} {...rest}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-6 py-4">
          <div className="min-w-0">
            {title && <h2 className="font-heading text-headline-sm font-semibold text-ink">{title}</h2>}
            {description && <p className="mt-0.5 text-body-md text-ink-muted">{description}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={cn(!flush && "p-6")}>{children}</div>
    </section>
  )
}
