import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

interface PageHeaderProps {
  title: string
  subtitle?: ReactNode
  /** Small link or control above the title, e.g. "All sources". */
  back?: ReactNode
  actions?: ReactNode
  align?: "left" | "center"
  className?: string
}

export function PageHeader({ title, subtitle, back, actions, align = "left", className }: PageHeaderProps) {
  const centered = align === "center"
  return (
    <div className={cn("flex flex-col gap-3", centered && "items-center text-center", className)}>
      {back}
      <div className={cn("flex w-full flex-wrap items-end justify-between gap-4", centered && "justify-center")}>
        <div className="min-w-0">
          <h1 className="font-heading text-headline-xl font-medium tracking-tight text-ink">{title}</h1>
          {subtitle && <p className="mt-2 max-w-2xl text-body-lg text-ink-muted">{subtitle}</p>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-3">{actions}</div>}
      </div>
    </div>
  )
}
