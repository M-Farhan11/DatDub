import { useEffect, useState } from "react"
import { Check, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

const STAGES = ["Creating tables", "Filling rows", "Applying rules", "Adding edge cases", "Checking everything"]
const STAGE_MS = 700

interface GeneratingCardProps {
  name: string
  /** e.g. "seed 42 · 5,000 customers · 3 edge cases" */
  summary: string
}

/**
 * Shown while POST /generate runs. The ticks are cosmetic timing: the last
 * stage stays active until the real response arrives.
 */
export function GeneratingCard({ name, summary }: GeneratingCardProps) {
  const [stage, setStage] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), STAGE_MS)
    return () => clearInterval(id)
  }, [])

  const progress = ((stage + 0.5) / STAGES.length) * 100

  return (
    <div className="mx-auto w-full max-w-[560px] px-gutter-lg pt-16 pb-24">
      <section
        aria-live="polite"
        aria-busy="true"
        className="rounded-xl border border-line bg-card p-8 shadow-md"
      >
        <h1 className="font-heading text-headline-lg font-medium text-ink">Generating {name}</h1>
        <p className="tabular mt-1 font-mono text-code-md text-ink-muted">{summary}</p>

        <ol className="mt-6 space-y-3">
          {STAGES.map((label, i) => {
            const done = i < stage
            const active = i === stage
            return (
              <li key={label} className="flex items-center gap-3">
                <span
                  className={cn(
                    "flex size-6 items-center justify-center rounded-full",
                    done && "bg-pass/10 text-pass",
                    active && "bg-primary-tint text-primary-deep",
                    !done && !active && "border border-line text-hint",
                  )}
                  aria-hidden="true"
                >
                  {done ? (
                    <Check className="size-3.5" strokeWidth={3} />
                  ) : active ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : null}
                </span>
                <span className={cn("text-body-md", done || active ? "text-ink" : "text-hint")}>
                  {label}
                  <span className="sr-only">{done ? " (done)" : active ? " (in progress)" : ""}</span>
                </span>
              </li>
            )
          })}
        </ol>

        <div
          className="mt-6 h-1.5 overflow-hidden rounded-full bg-surface-high"
          role="progressbar"
          aria-label="Generation progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(progress)}
        >
          <div className="h-full rounded-full bg-primary transition-[width] duration-500" style={{ width: `${progress}%` }} />
        </div>
      </section>
    </div>
  )
}
