import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

interface FieldProps {
  id: string
  label: string
  hint?: ReactNode
  error?: string | null
  /** Extra element next to the label, e.g. a value readout. */
  aside?: ReactNode
  className?: string
  children: ReactNode
}

/** Label + control + hint/error. The control must use the same `id`. */
export function Field({ id, label, hint, error, aside, className, children }: FieldProps) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="flex items-center justify-between gap-2">
        <label htmlFor={id} className="font-heading text-label-lg font-medium text-ink">
          {label}
        </label>
        {aside}
      </div>
      {children}
      {error ? (
        <p id={`${id}-error`} className="text-body-sm text-fail">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${id}-hint`} className="text-body-sm text-ink-muted">
            {hint}
          </p>
        )
      )}
    </div>
  )
}
