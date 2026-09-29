import { Shuffle, TriangleAlert } from "lucide-react"
import type { DatasetSchema } from "@/api/types"
import { Card } from "@/components/shared/Card"
import { Field } from "@/components/shared/Field"
import { SegmentedControl } from "@/components/shared/SegmentedControl"
import { SliderField } from "@/components/shared/SliderField"
import { formatInt } from "@/lib/format"
import { monoInputClass, textInputClass } from "@/lib/styles"
import { rootTables, type GenerationConfig } from "@/state/studioReducer"
import { estimateCells, estimateRows, MAX_ROWS_PER_TABLE, MAX_TOTAL_CELLS, rowsError } from "./estimates"

const PRESETS = [
  { value: "500", label: "Small 500" },
  { value: "5000", label: "Medium 5,000" },
  { value: "100000", label: "Large 100,000" },
]

const LOCALES = [
  ["en_US", "English (United States)"],
  ["en_GB", "English (United Kingdom)"],
  ["de_DE", "German (Germany)"],
  ["fr_FR", "French (France)"],
  ["es_ES", "Spanish (Spain)"],
  ["it_IT", "Italian (Italy)"],
  ["nl_NL", "Dutch (Netherlands)"],
  ["pt_BR", "Portuguese (Brazil)"],
  ["ja_JP", "Japanese (Japan)"],
] as const

interface SizeSettingsCardProps {
  schema: DatasetSchema
  config: GenerationConfig
  onRowsChange: (table: string, count: number) => void
  onConfigChange: (patch: Partial<GenerationConfig>) => void
  disabled?: boolean
}

export function SizeSettingsCard({ schema, config, onRowsChange, onConfigChange, disabled }: SizeSettingsCardProps) {
  const roots = rootTables(schema)
  const estimates = estimateRows(schema, config.rows)
  const children = schema.tables.filter((t) => !roots.includes(t))
  const tooLarge = schema.tables.filter((t) => (estimates.get(t.name) ?? 0) > MAX_ROWS_PER_TABLE)
  const cells = estimateCells(schema, estimates)
  const firstRoot = roots[0] ? config.rows[roots[0].name] : undefined
  const preset = PRESETS.find((p) => roots.every((t) => config.rows[t.name] === Number(p.value)))?.value ?? ""

  return (
    <Card title="Size and settings" description="How much data to create and how messy it should be.">
      <div className="space-y-6">
        <div className="space-y-3">
          <span className="font-heading text-label-lg font-medium text-ink">Presets</span>
          <SegmentedControl
            label="Dataset size preset"
            options={PRESETS}
            value={preset}
            disabled={disabled}
            onChange={(v) => roots.forEach((t) => onRowsChange(t.name, Number(v)))}
          />
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {roots.map((t) => {
            const value = config.rows[t.name]
            return (
              <Field key={t.name} id={`rows-${t.name}`} label={`Rows in ${t.name}`} error={rowsError(value)}>
                <input
                  id={`rows-${t.name}`}
                  inputMode="numeric"
                  value={value === undefined || Number.isNaN(value) ? "" : String(value)}
                  disabled={disabled}
                  onChange={(e) => {
                    const digits = e.target.value.replace(/\D/g, "")
                    onRowsChange(t.name, digits === "" ? Number.NaN : Number(digits))
                  }}
                  className={monoInputClass}
                />
              </Field>
            )
          })}
        </div>

        {children.length > 0 && firstRoot !== undefined && !Number.isNaN(firstRoot) && (
          <p className="text-body-sm text-ink-muted">
            Linked tables follow automatically, about{" "}
            {children.map((t, i) => (
              <span key={t.name}>
                {i > 0 && (i === children.length - 1 ? " and " : ", ")}
                <span className="tabular font-mono text-code-sm text-ink">{formatInt(estimates.get(t.name) ?? 0)}</span>{" "}
                {t.name.replace(/_/g, " ")}
              </span>
            ))}
            .
          </p>
        )}

        {(tooLarge.length > 0 || cells > MAX_TOTAL_CELLS) && (
          <div role="alert" className="flex items-start gap-2 rounded-lg border border-coral/40 bg-coral/10 px-3 py-2.5 text-body-md text-ink">
            <TriangleAlert className="mt-0.5 size-4 shrink-0 text-coral" aria-hidden="true" />
            <p>
              {tooLarge.length > 0
                ? `Large job: ${tooLarge.map((t) => t.name).join(", ")} would have more than ${formatInt(MAX_ROWS_PER_TABLE)} rows, which is above the per-table limit. Lower the row count.`
                : `Large job: about ${formatInt(cells)} values in total, above the ${formatInt(MAX_TOTAL_CELLS)} limit. Lower the row count.`}
            </p>
          </div>
        )}

        <Field id="seed" label="Seed" hint="Same seed gives the same data.">
          <div className="flex gap-2">
            <input
              id="seed"
              inputMode="numeric"
              value={String(config.seed)}
              disabled={disabled}
              onChange={(e) => onConfigChange({ seed: Number(e.target.value.replace(/\D/g, "") || 0) })}
              className={monoInputClass}
            />
            <button
              type="button"
              disabled={disabled}
              onClick={() => onConfigChange({ seed: Math.floor(Math.random() * 100_000) })}
              aria-label="Pick a random seed"
              title="Pick a random seed"
              className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-line bg-card text-ink-muted shadow-sm hover:border-primary hover:text-primary-deep disabled:opacity-50"
            >
              <Shuffle className="size-4" aria-hidden="true" />
            </button>
          </div>
        </Field>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <SliderField
            id="null-rate"
            label="Empty values"
            hint="Share of empty cells in columns that allow them."
            value={config.null_rate}
            max={0.5}
            disabled={disabled}
            onChange={(null_rate) => onConfigChange({ null_rate })}
          />
          <SliderField
            id="outlier-rate"
            label="Unusual values"
            hint="Share of numbers far outside the normal range."
            value={config.outlier_rate}
            max={0.5}
            disabled={disabled}
            onChange={(outlier_rate) => onConfigChange({ outlier_rate })}
          />
        </div>

        <Field id="locale" label="Locale" hint="Language and format of names, addresses and phone numbers.">
          <select
            id="locale"
            value={config.locale}
            disabled={disabled}
            onChange={(e) => onConfigChange({ locale: e.target.value })}
            className={textInputClass}
          >
            {LOCALES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
      </div>
    </Card>
  )
}
