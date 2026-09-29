interface SliderFieldProps {
  id: string
  label: string
  hint?: string
  /** 0..1 */
  value: number
  onChange: (value: number) => void
  /** upper bound as a ratio, e.g. 0.5 for 50% */
  max: number
  disabled?: boolean
}

/** Percentage slider stored as a ratio. */
export function SliderField({ id, label, hint, value, onChange, max, disabled }: SliderFieldProps) {
  const percent = Math.round(value * 1000) / 10
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <label htmlFor={id} className="font-heading text-label-lg font-medium text-ink">
          {label}
        </label>
        <span className="tabular font-mono text-code-md text-primary-deep">{percent}%</span>
      </div>
      <input
        id={id}
        type="range"
        min={0}
        max={max * 100}
        step={0.5}
        value={percent}
        disabled={disabled}
        aria-valuetext={`${percent}%`}
        aria-describedby={hint ? `${id}-hint` : undefined}
        onChange={(e) => onChange(Number(e.target.value) / 100)}
        className="h-2 w-full cursor-pointer accent-[var(--primary)] disabled:cursor-not-allowed"
      />
      {hint && (
        <p id={`${id}-hint`} className="text-body-sm text-ink-muted">
          {hint}
        </p>
      )}
    </div>
  )
}
