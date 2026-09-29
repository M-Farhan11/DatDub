import { cn } from "@/lib/utils"

interface ToggleProps {
  id: string
  label: string
  description?: string
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
}

/** Accessible on/off switch with a visible label. */
export function Toggle({ id, label, description, checked, onChange, disabled }: ToggleProps) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <label htmlFor={id} className="font-heading text-label-lg font-medium text-ink">
          {label}
        </label>
        {description && <p className="text-body-sm text-ink-muted">{description}</p>}
      </div>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative mt-0.5 inline-flex h-6 w-10 shrink-0 items-center rounded-full transition-colors disabled:opacity-50",
          checked ? "bg-primary" : "bg-line",
        )}
      >
        <span
          aria-hidden="true"
          className={cn(
            "inline-block size-5 rounded-full bg-card shadow-sm transition-transform",
            checked ? "translate-x-[18px]" : "translate-x-0.5",
          )}
        />
      </button>
    </div>
  )
}
