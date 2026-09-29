import { Minus, Plus } from "lucide-react"
import { cn } from "@/lib/utils"

interface CountStepperProps {
  value: number
  onChange: (value: number) => void
  min?: number
  max?: number
  label: string
  disabled?: boolean
}

/** Number input with - / + buttons, clamped to [min, max]. */
export function CountStepper({ value, onChange, min = 1, max = 1000, label, disabled }: CountStepperProps) {
  const commit = (input: HTMLInputElement) => {
    const n = Number(input.value)
    const clamped = input.value === "" || !Number.isFinite(n) ? value : Math.min(max, Math.max(min, Math.round(n)))
    input.value = String(clamped)
    if (clamped !== value) onChange(clamped)
  }

  const btn =
    "flex size-8 items-center justify-center text-ink-muted transition-colors hover:bg-surface-low hover:text-ink disabled:opacity-40 disabled:hover:bg-transparent"

  return (
    <div className={cn("inline-flex h-8 items-center overflow-hidden rounded-full border border-line bg-card", disabled && "opacity-60")}>
      <button
        type="button"
        className={btn}
        onClick={() => onChange(Math.max(min, value - 1))}
        disabled={disabled || value <= min}
        aria-label={`Decrease ${label}`}
      >
        <Minus className="size-3.5" aria-hidden="true" />
      </button>
      <input
        key={value}
        defaultValue={String(value)}
        inputMode="numeric"
        disabled={disabled}
        aria-label={label}
        onInput={(e) => {
          e.currentTarget.value = e.currentTarget.value.replace(/\D/g, "")
        }}
        onBlur={(e) => commit(e.currentTarget)}
        onKeyDown={(e) => e.key === "Enter" && commit(e.currentTarget)}
        className="tabular h-8 w-12 border-x border-line bg-transparent text-center font-mono text-code-md text-ink focus-visible:outline-offset-[-2px]"
      />
      <button
        type="button"
        className={btn}
        onClick={() => onChange(Math.min(max, value + 1))}
        disabled={disabled || value >= max}
        aria-label={`Increase ${label}`}
      >
        <Plus className="size-3.5" aria-hidden="true" />
      </button>
    </div>
  )
}
