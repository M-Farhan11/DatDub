import { Check } from "lucide-react"
import { cn } from "@/lib/utils"

const LABELS = ["Connect", "Choose tables", "Import"] as const

interface DbStepIndicatorProps {
  /** 0 = Connect, 1 = Choose tables, 2 = Import */
  current: number
}

export function DbStepIndicator({ current }: DbStepIndicatorProps) {
  return (
    <ol aria-label="Database steps" className="flex flex-wrap items-center gap-2">
      {LABELS.map((label, i) => {
        const done = i < current
        const active = i === current
        return (
          <li key={label} aria-current={active ? "step" : undefined} className="flex items-center gap-2">
            {i > 0 && <span className="h-px w-6 bg-line" aria-hidden="true" />}
            <span
              className={cn(
                "tabular flex size-5 items-center justify-center rounded-full font-heading text-[11px] leading-none",
                active && "bg-primary-deep font-bold text-white",
                done && "bg-primary-tint text-primary-deep",
                !active && !done && "border border-line text-ink-muted",
              )}
              aria-hidden="true"
            >
              {done ? <Check className="size-3" strokeWidth={3} /> : i + 1}
            </span>
            <span className={cn("font-heading text-label-lg", active ? "font-medium text-ink" : "text-ink-muted")}>
              {label}
            </span>
          </li>
        )
      })}
    </ol>
  )
}
