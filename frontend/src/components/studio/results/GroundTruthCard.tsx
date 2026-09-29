import { useState } from "react"
import { ArrowRight } from "lucide-react"
import type { GroundTruthEntry } from "@/api/types"
import { MonoText } from "@/components/shared/MonoText"
import { humanize } from "@/lib/format"

const PREVIEW = 12

interface GroundTruthCardProps {
  entry: GroundTruthEntry
  title?: string
  onViewRows: () => void
}

export function GroundTruthCard({ entry, title, onViewRows }: GroundTruthCardProps) {
  const [expanded, setExpanded] = useState(false)
  const ids = expanded ? entry.affected_ids : entry.affected_ids.slice(0, PREVIEW)
  const hidden = entry.affected_ids.length - PREVIEW

  return (
    <article className="rounded-xl border border-line bg-card p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-heading text-headline-sm font-medium text-ink">{title ?? entry.description}</h3>
          {title && <p className="mt-0.5 text-body-md text-ink-muted">{entry.description}</p>}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="rounded-full bg-expected/10 px-2.5 py-0.5 font-heading text-label-md font-medium text-expected">
            {humanize(entry.kind)}
          </span>
          <MonoText className="rounded-full bg-surface-high px-2.5 py-0.5 text-code-sm text-primary-deep">{entry.table}</MonoText>
        </div>
      </div>

      <div className="mt-4">
        <p className="text-body-sm text-ink-muted">
          {entry.affected_ids.length} {entry.affected_ids.length === 1 ? "record" : "records"}
        </p>
        <ul className="mt-2 flex flex-wrap gap-1.5" aria-label="Affected IDs">
          {ids.map((id) => (
            <li key={id}>
              <MonoText className="rounded-md bg-surface-low px-2 py-0.5 text-code-sm text-ink">{id}</MonoText>
            </li>
          ))}
          {hidden > 0 && (
            <li>
              <button
                type="button"
                onClick={() => setExpanded((v) => !v)}
                className="rounded-md px-2 py-0.5 font-heading text-label-md font-medium text-primary-deep hover:underline"
              >
                {expanded ? "Show fewer" : `Show all ${entry.affected_ids.length}`}
              </button>
            </li>
          )}
        </ul>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3">
        <p className="text-body-md text-ink">
          <span className="font-medium">Expected:</span> {entry.expected_behavior}
        </p>
        <button
          type="button"
          onClick={onViewRows}
          className="inline-flex items-center gap-1 rounded-sm font-heading text-label-lg font-medium text-primary-deep hover:underline"
        >
          View rows
          <ArrowRight className="size-4" aria-hidden="true" />
        </button>
      </div>
    </article>
  )
}
