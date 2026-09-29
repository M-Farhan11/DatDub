import { ShieldCheck } from "lucide-react"
import type { ExtractMode } from "@/api/types"
import { Field } from "@/components/shared/Field"
import { SegmentedControl } from "@/components/shared/SegmentedControl"
import { monoInputClass } from "@/lib/styles"
import { cn } from "@/lib/utils"
import { sampleLimitError } from "./dbValidation"

const MODES = [
  { value: "schema_only" as const, label: "Structure only" },
  { value: "schema_and_sample" as const, label: "Structure + sample rows" },
]

interface DbExtractOptionsProps {
  mode: ExtractMode
  onModeChange: (mode: ExtractMode) => void
  sampleLimit: string
  onSampleLimitChange: (value: string) => void
  disabled?: boolean
}

export function DbExtractOptions({ mode, onModeChange, sampleLimit, onSampleLimitChange, disabled }: DbExtractOptionsProps) {
  const sampling = mode === "schema_and_sample"
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-6">
        <div className="flex flex-col gap-1.5">
          <span className="font-heading text-label-lg font-medium text-ink">What to read</span>
          <SegmentedControl label="What to read" options={MODES} value={mode} onChange={onModeChange} disabled={disabled} />
        </div>
        <Field
          id="db-sample"
          label="Sample rows per table"
          error={sampling ? sampleLimitError(sampleLimit) : null}
          className={cn("w-48", !sampling && "opacity-60")}
        >
          <input
            id="db-sample"
            inputMode="numeric"
            value={sampleLimit}
            onChange={(e) => onSampleLimitChange(e.target.value.replace(/\D/g, ""))}
            disabled={disabled || !sampling}
            className={monoInputClass}
          />
        </Field>
      </div>
      <p className="flex items-start gap-2 text-body-sm text-ink-muted">
        <ShieldCheck className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
        {sampling
          ? "Sample rows are used for statistics only, then discarded. They are never stored or sent to the AI."
          : "Only table structure is read. No rows leave the database."}
      </p>
    </div>
  )
}
