import type { ScenarioSelection } from "@/api/types"
import { Card } from "@/components/shared/Card"
import { CopyButton } from "@/components/shared/CopyButton"
import { MonoText } from "@/components/shared/MonoText"
import { formatInt, formatPercent } from "@/lib/format"
import type { GenerationConfig } from "@/state/studioReducer"

interface RecreateCardProps {
  schemaName: string
  config: GenerationConfig
  scenarios: ScenarioSelection[]
}

/** Settings needed to regenerate the exact same dataset (same schema + seed + settings). */
export function RecreateCard({ schemaName, config, scenarios }: RecreateCardProps) {
  const recipe = {
    schema: schemaName,
    seed: config.seed,
    rows: config.rows,
    null_rate: config.null_rate,
    outlier_rate: config.outlier_rate,
    locale: config.locale,
    scenarios: scenarios.map((s) => ({ id: s.proposal.id, title: s.proposal.title, count: s.count })),
  }

  const items: [string, string][] = [
    ["Seed", String(config.seed)],
    ["Rows", Object.entries(config.rows).map(([t, n]) => `${formatInt(n)} ${t}`).join(", ")],
    ["Empty values", formatPercent(config.null_rate, 1)],
    ["Unusual values", formatPercent(config.outlier_rate, 1)],
    ["Locale", config.locale],
    ["Edge cases", scenarios.length ? scenarios.map((s) => `${s.proposal.title} (${s.count})`).join(", ") : "None"],
  ]

  return (
    <Card
      title="To recreate this dataset"
      description="Use the same schema with these settings to get identical data."
      actions={<CopyButton text={JSON.stringify(recipe, null, 2)} />}
    >
      <dl className="grid grid-cols-1 items-baseline gap-x-6 gap-y-3 sm:grid-cols-[140px_minmax(0,1fr)]">
        {items.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-body-md text-ink-muted">{label}</dt>
            <dd>
              <MonoText className="text-ink">{value}</MonoText>
            </dd>
          </div>
        ))}
      </dl>
    </Card>
  )
}
