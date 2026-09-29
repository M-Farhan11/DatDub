import type { Rule, ValidationReport } from "@/api/types"
import { MonoText } from "@/components/shared/MonoText"
import { StatusTag } from "@/components/shared/StatusTag"
import { formatPercent } from "@/lib/format"
import { describeCheckName } from "@/lib/ruleText"
import { cn } from "@/lib/utils"
import { checkStatus, summarizeReport } from "./reportSummary"
import { StatCard } from "./StatCard"

const pct = (v: number | null) => (v === null ? "—" : formatPercent(v, v === 1 ? 0 : 1))

export function ChecksTab({ report, rules }: { report: ValidationReport; rules: Rule[] }) {
  const stats = summarizeReport(report)
  return (
    <div className="space-y-6">
      <div className={cn("grid grid-cols-2 gap-4", stats.similarity !== null ? "lg:grid-cols-4" : "lg:grid-cols-3")}>
        <StatCard label="Unique keys" value={pct(stats.uniqueKeys)} hint="No duplicate primary keys" />
        <StatCard label="Valid links" value={pct(stats.validLinks)} hint="Every foreign key finds its parent" />
        <StatCard label="Rules passed" value={`${stats.rulesPassed}/${stats.rulesTotal}`} hint="Edge cases count as expected" />
        {stats.similarity !== null && (
          <StatCard label="Similarity to sample" value={pct(stats.similarity)} hint="How closely values follow your sample" />
        )}
      </div>

      <div className="overflow-x-auto rounded-xl border border-line bg-card shadow-sm">
        <table className="w-full min-w-[640px] border-collapse text-left">
          <caption className="sr-only">Validation checks</caption>
          <thead className="bg-surface-low font-heading text-label-md text-ink-muted">
            <tr>
              <th scope="col" className="px-5 py-3 font-medium">Check</th>
              <th scope="col" className="px-3 py-3 font-medium">Table</th>
              <th scope="col" className="px-3 py-3 font-medium">Status</th>
              <th scope="col" className="px-5 py-3 font-medium">Detail</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {report.checks.map((check, i) => (
              <tr key={`${check.name}-${check.table}-${i}`}>
                <td className="px-5 py-3 text-body-md text-ink">{describeCheckName(check.name, rules)}</td>
                <td className="px-3 py-3">
                  <MonoText className="text-ink-muted">{check.table}</MonoText>
                </td>
                <td className="px-3 py-3">
                  <StatusTag status={checkStatus(check)} />
                </td>
                <td className="px-5 py-3">
                  <MonoText className="text-code-sm text-ink-muted">{check.detail}</MonoText>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap gap-x-6 gap-y-2 text-body-sm text-ink-muted">
        <span className="flex items-center gap-2">
          <StatusTag status="pass" /> The check found no problems.
        </span>
        <span className="flex items-center gap-2">
          <StatusTag status="expected" /> Only the edge cases you added break it, on purpose.
        </span>
        <span className="flex items-center gap-2">
          <StatusTag status="fail" /> Some rows break it unexpectedly.
        </span>
      </div>
    </div>
  )
}
