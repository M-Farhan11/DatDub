import { Fragment } from "react"
import { Check } from "lucide-react"
import { cn } from "@/lib/utils"
import { STEPS, type Step } from "./steps"

interface StepperProps {
  current: Step
  /** Index of the furthest step reached; steps up to it are clickable. */
  reached: number
  onSelect: (step: Step) => void
}

export function Stepper({ current, reached, onSelect }: StepperProps) {
  const currentIdx = STEPS.indexOf(current)
  return (
    <nav aria-label="Workflow steps">
      <ol className="flex items-center gap-2">
        {STEPS.map((step, i) => {
          const isCurrent = step === current
          const clickable = i <= reached && !isCurrent
          const done = i <= reached && i !== currentIdx
          const content = (
            <>
              <span
                className={cn(
                  "tabular flex size-5 items-center justify-center rounded-full font-heading text-[11px] leading-none",
                  isCurrent && "bg-primary-deep font-bold text-white",
                  !isCurrent && done && "bg-primary-tint text-primary-deep",
                  !isCurrent && !done && "border border-line text-ink-muted",
                )}
                aria-hidden="true"
              >
                {!isCurrent && done ? <Check className="size-3" strokeWidth={3} /> : i + 1}
              </span>
              <span
                className={cn(
                  "font-heading text-label-lg",
                  isCurrent ? "font-medium text-ink" : "hidden text-ink-muted lg:inline",
                  clickable && "group-hover:text-ink",
                )}
              >
                {step}
              </span>
            </>
          )
          return (
            <Fragment key={step}>
              {i > 0 && <li aria-hidden="true" className="h-px w-3 bg-line sm:w-6" />}
              <li aria-current={isCurrent ? "step" : undefined}>
                {clickable ? (
                  <button
                    type="button"
                    onClick={() => onSelect(step)}
                    className="group flex items-center gap-1 rounded-full px-1 py-0.5"
                    aria-label={`Go to step ${i + 1}: ${step}`}
                  >
                    {content}
                  </button>
                ) : (
                  <span
                    className={cn("flex items-center gap-1 px-1 py-0.5", !isCurrent && "cursor-not-allowed opacity-70")}
                    aria-disabled={!isCurrent || undefined}
                  >
                    {content}
                  </span>
                )}
              </li>
            </Fragment>
          )
        })}
      </ol>
    </nav>
  )
}
