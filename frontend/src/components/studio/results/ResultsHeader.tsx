import type { GenerateResponse } from "@/api/types"
import { StatusTag } from "@/components/shared/StatusTag"
import { formatInt } from "@/lib/format"

interface ResultsHeaderProps {
  name: string
  seed: number
  result: GenerateResponse
}

export function ResultsHeader({ name, seed, result }: ResultsHeaderProps) {
  const rows = Object.values(result.row_counts).reduce((a, b) => a + b, 0)
  const tables = Object.keys(result.row_counts).length
  const edgeCases = result.ground_truth.length
  const passed = result.report.overall === "PASS"
  return (
    <section className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-line bg-card px-6 py-5 shadow-sm">
      <div className="min-w-0">
        <h1 className="truncate font-heading text-headline-lg font-medium text-ink">{name}</h1>
        <p className="tabular mt-1 font-mono text-code-md text-ink-muted">
          seed {seed} · {formatInt(rows)} rows · {tables} tables · {edgeCases} edge {edgeCases === 1 ? "case" : "cases"}
        </p>
      </div>
      <StatusTag
        status={passed ? "pass" : "fail"}
        label={passed ? "All checks passed" : "Some checks failed"}
        className="h-8 px-3 text-label-lg"
      />
    </section>
  )
}
