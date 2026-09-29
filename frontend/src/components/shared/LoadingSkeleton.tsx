import { cn } from "@/lib/utils"

interface LoadingSkeletonProps {
  /** Number of placeholder lines. */
  lines?: number
  /** Height class for each line, e.g. "h-4" or "h-10". */
  lineClassName?: string
  className?: string
  label?: string
}

export function LoadingSkeleton({ lines = 3, lineClassName = "h-4", className, label = "Loading" }: LoadingSkeletonProps) {
  return (
    <div role="status" aria-live="polite" className={cn("flex flex-col gap-3", className)}>
      <span className="sr-only">{label}</span>
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          aria-hidden="true"
          className={cn("animate-pulse rounded-lg bg-surface-high", lineClassName)}
          style={{ width: `${100 - ((i * 13) % 30)}%` }}
        />
      ))}
    </div>
  )
}
