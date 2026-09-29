import type { ReactNode } from "react"

interface StatCardProps {
  label: string
  value: ReactNode
  hint?: string
}

export function StatCard({ label, value, hint }: StatCardProps) {
  return (
    <div className="rounded-xl border border-line bg-card p-5 shadow-sm">
      <p className="text-body-sm text-ink-muted">{label}</p>
      <p className="tabular mt-1 font-mono text-headline-lg font-medium text-ink">{value}</p>
      {hint && <p className="mt-1 text-body-sm text-hint">{hint}</p>}
    </div>
  )
}
