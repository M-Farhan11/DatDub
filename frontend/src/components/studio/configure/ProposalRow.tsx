import type { ScenarioProposal } from "@/api/types"
import { CountStepper } from "@/components/shared/CountStepper"
import { MonoText } from "@/components/shared/MonoText"
import { cn } from "@/lib/utils"

interface ProposalRowProps {
  proposal: ScenarioProposal
  /** undefined when not selected */
  count: number | undefined
  onToggle: (on: boolean) => void
  onCountChange: (count: number) => void
  disabled?: boolean
}

export function ProposalRow({ proposal, count, onToggle, onCountChange, disabled }: ProposalRowProps) {
  const selected = count !== undefined
  const id = `proposal-${proposal.id}`
  return (
    <li className={cn("flex items-start gap-3 px-4 py-3.5 transition-colors", selected && "bg-surface-low")}>
      <input
        id={id}
        type="checkbox"
        checked={selected}
        disabled={disabled}
        onChange={(e) => onToggle(e.target.checked)}
        className="mt-1 size-4 shrink-0 cursor-pointer accent-[var(--primary)] disabled:cursor-not-allowed"
      />
      <div className="min-w-0 flex-1">
        <label htmlFor={id} className="cursor-pointer font-heading text-label-lg font-medium text-ink">
          {proposal.title}
        </label>
        <MonoText className="mt-0.5 block text-code-sm text-hint">
          {proposal.table}
          {proposal.column ? `.${proposal.column}` : ""}
        </MonoText>
        <p className="mt-1 text-body-sm text-ink-muted">Expected: {proposal.expected_behavior}</p>
      </div>
      <CountStepper
        value={count ?? proposal.suggested_count}
        onChange={onCountChange}
        min={1}
        max={1000}
        label={`Records for ${proposal.title}`}
        disabled={disabled || !selected}
      />
    </li>
  )
}
