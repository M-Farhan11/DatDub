import { Info } from "lucide-react"

interface NoteBarProps {
  notes: string[]
  autoAdded: string[]
}

/** Slim bar with the first AI note and any auto-added tables. */
export function NoteBar({ notes, autoAdded }: NoteBarProps) {
  const parts = [
    ...(notes[0] ? [notes[0]] : []),
    ...(autoAdded.length ? [`Added automatically to keep links intact: ${autoAdded.join(", ")}.`] : []),
  ]
  if (parts.length === 0) return null
  const more = notes.length - 1
  return (
    <div className="flex items-start gap-2 rounded-lg border border-primary/15 bg-primary-tint/40 px-3 py-2 text-body-md text-ink">
      <Info className="mt-0.5 size-4 shrink-0 text-primary-deep" aria-hidden="true" />
      <p className="min-w-0">
        {parts.join(" ")}
        {more > 0 && (
          <span className="text-ink-muted" title={notes.slice(1).join("\n")}>
            {" "}
            (+{more} more {more === 1 ? "note" : "notes"})
          </span>
        )}
      </p>
    </div>
  )
}
