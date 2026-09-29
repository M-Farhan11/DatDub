import type { ColumnProfile } from "@/api/types"
import { MonoText } from "@/components/shared/MonoText"
import { formatPercent } from "@/lib/format"

const fmt = (v: number | string | null) =>
  v === null ? "—" : typeof v === "number" ? v.toLocaleString("en-US", { maximumFractionDigits: 2 }) : v

/** Statistics learned from sample rows (only present for CSV / database samples). */
export function ProfileSummary({ profile }: { profile: ColumnProfile }) {
  const stats: [string, string][] = [
    ["Empty values", formatPercent(profile.null_rate, 1)],
    ...(profile.unique_ratio !== null ? ([["Unique values", formatPercent(profile.unique_ratio, 1)]] as [string, string][]) : []),
    ...(profile.mean !== null ? ([["Average", fmt(profile.mean)]] as [string, string][]) : []),
    ...(profile.min !== null || profile.max !== null ? ([["Range", `${fmt(profile.min)} to ${fmt(profile.max)}`]] as [string, string][]) : []),
  ]
  return (
    <div className="space-y-3">
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
        {stats.map(([label, value]) => (
          <div key={label}>
            <dt className="text-body-sm text-ink-muted">{label}</dt>
            <dd>
              <MonoText className="text-ink">{value}</MonoText>
            </dd>
          </div>
        ))}
      </dl>
      {profile.top_values && profile.top_values.length > 0 && (
        <div>
          <p className="text-body-sm text-ink-muted">Most common values</p>
          <ul className="mt-2 space-y-1.5">
            {profile.top_values.slice(0, 5).map(([value, share]) => (
              <li key={value} className="flex items-center gap-2">
                <MonoText className="w-28 shrink-0 truncate text-code-sm text-ink">{value}</MonoText>
                <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-high" aria-hidden="true">
                  <span className="block h-full rounded-full bg-primary" style={{ width: `${share * 100}%` }} />
                </span>
                <MonoText className="w-12 text-right text-code-sm text-ink-muted">{formatPercent(share)}</MonoText>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
