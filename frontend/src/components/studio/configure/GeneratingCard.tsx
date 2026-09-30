import { useEffect, useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import { Check, DatabaseZap, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

const STAGES = ["Creating tables and links", "Filling rows", "Adding edge cases", "Checking every rule"]
const STAGE_MS = 800

interface GeneratingCardProps {
  name: string
  /** e.g. "seed 42 · 5,000 customers · 3 edge cases" */
  summary: string
}

/**
 * Shown while POST /generate runs, centered in the viewport. The ticks are
 * cosmetic timing: the last stage stays active until the real response arrives.
 */
export function GeneratingCard({ name, summary }: GeneratingCardProps) {
  const [stage, setStage] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), STAGE_MS)
    return () => clearInterval(id)
  }, [])

  const progress = ((stage + 0.5) / STAGES.length) * 100

  return (
    <div className="flex min-h-[calc(100dvh-4rem)] w-full items-center justify-center px-gutter-lg py-12">
      <motion.section
        aria-live="polite"
        aria-busy="true"
        initial={{ opacity: 0, y: 16, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ type: "spring", stiffness: 220, damping: 24 }}
        className="w-full max-w-[520px] rounded-2xl border border-line bg-card p-8 text-center shadow-xl shadow-primary/10"
      >
        <span className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-primary-tint text-primary-deep">
          <DatabaseZap className="size-7 animate-pulse" aria-hidden="true" />
        </span>
        <h1 className="mt-5 font-heading text-headline-lg font-medium text-ink">Generating {name}</h1>
        <p className="tabular mt-1 font-mono text-code-md text-ink-muted">{summary}</p>

        <div
          className="mt-7 h-1.5 overflow-hidden rounded-full bg-surface-high"
          role="progressbar"
          aria-label="Generation progress"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(progress)}
        >
          <motion.div
            className="h-full rounded-full bg-primary"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ type: "spring", stiffness: 80, damping: 20 }}
          />
        </div>

        <ol className="mx-auto mt-7 w-fit space-y-3 text-left">
          {STAGES.map((label, i) => {
            const done = i < stage
            const active = i === stage
            return (
              <li key={label} className="flex items-center gap-3">
                <span
                  className={cn(
                    "flex size-6 items-center justify-center rounded-full transition-colors duration-300",
                    done && "bg-pass/10 text-pass",
                    active && "bg-primary-tint text-primary-deep",
                    !done && !active && "border border-line text-hint",
                  )}
                  aria-hidden="true"
                >
                  <AnimatePresence mode="wait" initial={false}>
                    {done ? (
                      <motion.span key="done" initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 500, damping: 22 }}>
                        <Check className="size-3.5" strokeWidth={3} />
                      </motion.span>
                    ) : active ? (
                      <motion.span key="active" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                        <Loader2 className="size-3.5 animate-spin" />
                      </motion.span>
                    ) : null}
                  </AnimatePresence>
                </span>
                <span className={cn("text-body-md transition-colors duration-300", done || active ? "text-ink" : "text-hint")}>
                  {label}
                  <span className="sr-only">{done ? " (done)" : active ? " (in progress)" : ""}</span>
                </span>
              </li>
            )
          })}
        </ol>
      </motion.section>
    </div>
  )
}
