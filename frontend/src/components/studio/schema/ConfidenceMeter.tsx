import { formatPercent } from "@/lib/format"
import { cn } from "@/lib/utils"

/** "AI confidence NN%" with a thin bar. Below 80% it asks for a check. */
export function ConfidenceMeter({ value }: { value: number }) {
  const low = value < 0.8
  return (
    <div>
      <div className="flex items-center justify-between text-body-sm">
        <span className="text-ink-muted">AI confidence</span>
        <span className={cn("tabular font-mono text-code-md font-medium", low ? "text-expected" : "text-ink")}>
          {formatPercent(value)}
        </span>
      </div>
      <div
        className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-high"
        role="meter"
        aria-label="AI confidence"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(value * 100)}
      >
        <div className={cn("h-full rounded-full", low ? "bg-expected" : "bg-primary")} style={{ width: `${value * 100}%` }} />
      </div>
      {low && <p className="mt-1.5 text-body-sm text-expected">Low confidence. Check the semantic type below.</p>}
    </div>
  )
}
