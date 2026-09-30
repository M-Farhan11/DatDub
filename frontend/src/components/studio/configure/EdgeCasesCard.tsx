import { useState } from "react"
import { FlaskConical } from "lucide-react"
import { errorMessage, proposeScenarios } from "@/api/client"
import type { DatasetSchema, ScenarioProposal } from "@/api/types"
import { Card } from "@/components/shared/Card"
import { ErrorCallout } from "@/components/shared/ErrorCallout"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { SubmitButton } from "@/components/shared/SubmitButton"
import { formatInt } from "@/lib/format"
import { textInputClass } from "@/lib/styles"
import { ProposalRow } from "./ProposalRow"

interface EdgeCasesCardProps {
  schema: DatasetSchema
  instruction: string
  onInstructionChange: (value: string) => void
  proposals: ScenarioProposal[]
  onProposals: (proposals: ScenarioProposal[]) => void
  selected: Record<string, number>
  onToggle: (id: string, on: boolean) => void
  onCountChange: (id: string, count: number) => void
  disabled?: boolean
}

export function EdgeCasesCard({
  schema,
  instruction,
  onInstructionChange,
  proposals,
  onProposals,
  selected,
  onToggle,
  onCountChange,
  disabled,
}: EdgeCasesCardProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const selectedCount = Object.keys(selected).length
  const records = Object.values(selected).reduce((a, b) => a + b, 0)

  const suggest = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await proposeScenarios(schema, instruction.trim())
      onProposals(res.proposals)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card
      title="Edge cases"
      description="Tricky records added on purpose, so you can test how your app handles them. Each one is listed in the answer key."
      flush
    >
      <div className="space-y-3 border-b border-line p-6">
        <label htmlFor="instruction" className="font-heading text-label-lg font-medium text-ink">
          What should the data test?
        </label>
        <div className="flex gap-2">
          <input
            id="instruction"
            value={instruction}
            onChange={(e) => onInstructionChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && instruction.trim() && !loading && void suggest()}
            disabled={disabled || loading}
            placeholder="For example: late payments and duplicate customers"
            className={textInputClass}
          />
          <SubmitButton
            loading={loading}
            loadingLabel="Suggesting…"
            disabled={disabled || instruction.trim() === ""}
            onClick={suggest}
          >
            Suggest
          </SubmitButton>
        </div>
        {error && <ErrorCallout title="No suggestions this time" message={error} />}
      </div>

      {loading ? (
        <div className="p-6">
          <LoadingSkeleton lines={4} lineClassName="h-12" label="Suggesting edge cases" />
        </div>
      ) : proposals.length === 0 ? (
        <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
          <FlaskConical className="size-6 text-hint" aria-hidden="true" />
          <p className="max-w-sm text-body-md text-ink-muted">
            No edge cases yet. Click Suggest to get ideas that fit this schema, or generate clean data without them.
          </p>
        </div>
      ) : (
        <ul aria-label="Suggested edge cases" className="divide-y divide-line">
          {proposals.map((p) => (
            <ProposalRow
              key={p.id}
              proposal={p}
              count={selected[p.id]}
              onToggle={(on) => onToggle(p.id, on)}
              onCountChange={(n) => onCountChange(p.id, n)}
              disabled={disabled}
            />
          ))}
        </ul>
      )}

      <footer className="tabular border-t border-line px-6 py-3 text-body-sm text-ink-muted">
        {selectedCount} selected · {formatInt(records)} records
      </footer>
    </Card>
  )
}
