import { FlaskConical } from "lucide-react"
import type { GroundTruthEntry, ScenarioProposal } from "@/api/types"
import { CopyButton } from "@/components/shared/CopyButton"
import { EmptyState } from "@/components/shared/EmptyState"
import { Button } from "@/components/ui/button"
import { GroundTruthCard } from "./GroundTruthCard"

interface EdgeCasesTabProps {
  groundTruth: GroundTruthEntry[]
  proposals: ScenarioProposal[]
  onViewRows: (table: string) => void
  onAddEdgeCases: () => void
}

export function EdgeCasesTab({ groundTruth, proposals, onViewRows, onAddEdgeCases }: EdgeCasesTabProps) {
  if (groundTruth.length === 0) {
    return (
      <EmptyState
        icon={FlaskConical}
        title="No edge cases were added"
        description="This dataset is clean. Add edge cases in Configure to test how your app handles tricky records."
        action={<Button onClick={onAddEdgeCases}>Add edge cases</Button>}
      />
    )
  }

  const titleOf = (id: string) => proposals.find((p) => p.id === id)?.title

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-heading text-headline-md font-medium text-ink">Records changed on purpose</h2>
          <p className="mt-0.5 text-body-md text-ink-muted">Use this list as the answer key for your tests.</p>
        </div>
        <CopyButton text={JSON.stringify(groundTruth, null, 2)} label="Copy JSON" />
      </div>
      {groundTruth.map((entry) => (
        <GroundTruthCard
          key={entry.scenario_id}
          entry={entry}
          title={titleOf(entry.scenario_id)}
          onViewRows={() => onViewRows(entry.table)}
        />
      ))}
    </div>
  )
}
