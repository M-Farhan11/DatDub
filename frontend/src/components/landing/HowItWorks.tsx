import { useState } from "react"
import { motion, useAnimationFrame, useMotionValue, useReducedMotion } from "motion/react"
import { FlaskConical, Network, PackageCheck, Pause, Play, Upload, type LucideIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import { SectionHeading } from "./SectionHeading"

const STEPS: { icon: LucideIcon; title: string; body: string; detail: string }[] = [
  {
    icon: Upload,
    title: "Bring your structure",
    body: "Describe your system, upload CSV files, connect Postgres or pick a template.",
    detail: "prompt · csv · postgres · template",
  },
  {
    icon: Network,
    title: "Review the schema",
    body: "See every table and link on a graph. Correct types and personal-data flags.",
    detail: "4 tables · 7 links · 3 PII columns",
  },
  {
    icon: FlaskConical,
    title: "Add edge cases",
    body: "Pick the tricky records to include: overpayments, duplicates, missing values.",
    detail: "+ overpayment  + leap-day date",
  },
  {
    icon: PackageCheck,
    title: "Generate, check, export",
    body: "Get a validation report, invoice PDFs and your data as CSV, JSON or a ZIP.",
    detail: "42 checks passed · dataset.zip",
  },
]

const STEP_MS = 3400

/**
 * The four steps stay visible; a highlight walks across them one at a time.
 * Pauses on hover or keyboard focus, has a pause button, and does not
 * advance at all when the visitor prefers reduced motion.
 */
export function HowItWorks() {
  const reduce = useReducedMotion()
  const [active, setActive] = useState(0)
  const [userPaused, setUserPaused] = useState(false)
  const [hovered, setHovered] = useState(false)
  const progress = useMotionValue(0)
  const running = !reduce && !userPaused && !hovered

  useAnimationFrame((_, delta) => {
    if (!running) return
    const next = progress.get() + delta / STEP_MS
    if (next >= 1) {
      progress.set(0)
      setActive((a) => (a + 1) % STEPS.length)
    } else progress.set(next)
  })

  const select = (i: number) => {
    progress.set(0)
    setActive(i)
  }

  return (
    <section id="how-it-works" aria-labelledby="how-it-works-title" className="w-full scroll-mt-16 py-20 md:py-24">
      <div className="mx-auto max-w-[1160px] px-margin md:px-margin-lg">
        <SectionHeading
          id="how-it-works-title"
          title="How it works"
          subtitle="Four steps from an idea to a checked test database. You review everything before a row is generated."
        />
        {!reduce && (
          <div className="mt-6 flex justify-center">
            <button
              type="button"
              onClick={() => setUserPaused((p) => !p)}
              className="inline-flex h-9 items-center gap-2 rounded-full border border-chrome bg-card px-4 font-heading text-label-md font-medium text-ink-muted transition-colors hover:text-ink"
            >
              {userPaused ? <Play className="size-3.5" aria-hidden="true" /> : <Pause className="size-3.5" aria-hidden="true" />}
              {userPaused ? "Play the walkthrough" : "Pause the walkthrough"}
            </button>
          </div>
        )}

        <ol
          className="relative mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
          onFocus={() => setHovered(true)}
          onBlur={() => setHovered(false)}
        >
          {/* Track line behind the cards on wide screens */}
          <span aria-hidden="true" className="absolute top-[46px] right-[12%] left-[12%] hidden h-px bg-chrome lg:block" />
          {STEPS.map(({ icon: Icon, title, body, detail }, i) => {
            const isActive = i === active
            return (
              <li key={title} className="relative">
                <button
                  type="button"
                  onClick={() => select(i)}
                  aria-current={isActive ? "step" : undefined}
                  className={cn(
                    "relative flex h-full w-full flex-col overflow-hidden rounded-2xl border bg-card p-6 text-left transition-[box-shadow,transform,border-color] duration-300",
                    isActive ? "-translate-y-1 border-transparent shadow-xl shadow-primary/10" : "border-line shadow-sm",
                  )}
                >
                  {isActive && (
                    <motion.span
                      layoutId="how-highlight"
                      aria-hidden="true"
                      className="pointer-events-none absolute inset-0 rounded-2xl border-2 border-primary"
                      transition={{ type: "spring", stiffness: 260, damping: 30 }}
                    />
                  )}
                  <span className="flex items-center gap-3">
                    <span
                      className={cn(
                        "flex size-11 items-center justify-center rounded-xl transition-colors duration-300",
                        isActive ? "bg-primary text-primary-foreground" : "bg-primary-tint text-primary-deep",
                      )}
                    >
                      <Icon className="size-5" aria-hidden="true" />
                    </span>
                    <span className="font-heading text-label-md text-hint">Step {i + 1}</span>
                  </span>
                  <span className="mt-5 font-heading text-headline-sm font-medium text-ink">{title}</span>
                  <span className="mt-2 text-body-md text-ink-muted">{body}</span>
                  <span
                    className={cn(
                      "mt-5 rounded-lg px-3 py-2 font-mono text-code-sm transition-colors duration-300",
                      isActive ? "bg-primary-tint text-primary-deep" : "bg-surface-low text-hint",
                    )}
                  >
                    {detail}
                  </span>
                  {isActive && !reduce && (
                    <motion.span
                      aria-hidden="true"
                      className="absolute inset-x-0 bottom-0 h-1 origin-left bg-primary"
                      style={{ scaleX: progress }}
                    />
                  )}
                </button>
              </li>
            )
          })}
        </ol>
      </div>
    </section>
  )
}
