import { ArrowRight, CircleCheck, Info } from "lucide-react"
import type { FromDbResponse } from "@/api/types"
import { MonoText } from "@/components/shared/MonoText"
import { Button } from "@/components/ui/button"
import { formatInt } from "@/lib/format"

interface DbImportResultProps {
  result: FromDbResponse
  onContinue: () => void
}

export function DbImportResult({ result, onContinue }: DbImportResultProps) {
  const tableCount = result.schema.tables.length
  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3">
        <CircleCheck className="mt-0.5 size-6 shrink-0 text-pass" aria-hidden="true" />
        <div>
          <p className="font-heading text-headline-sm font-medium text-ink">
            Imported {tableCount} {tableCount === 1 ? "table" : "tables"}
          </p>
          <p className="mt-0.5 text-body-md text-ink-muted">
            {result.rows_sampled > 0
              ? `${formatInt(result.rows_sampled)} sample rows were profiled, then discarded.`
              : "Only the table structure was read."}
          </p>
        </div>
      </div>

      {result.auto_added.length > 0 && (
        <div className="flex items-start gap-3 rounded-xl border border-primary/20 bg-primary-tint/40 px-4 py-3 text-body-md text-ink">
          <Info className="mt-0.5 size-5 shrink-0 text-primary-deep" aria-hidden="true" />
          <p>
            Added automatically:{" "}
            {result.auto_added.map((name, i) => (
              <span key={name}>
                {i > 0 && ", "}
                <MonoText>{name}</MonoText>
              </span>
            ))}
            . Your tables link to {result.auto_added.length === 1 ? "it" : "them"}, so {result.auto_added.length === 1 ? "it is" : "they are"} needed to keep the data connected.
          </p>
        </div>
      )}

      {result.notes.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-body-md text-ink-muted">
          {result.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}

      <div className="flex justify-end">
        <Button onClick={onContinue}>
          Review the schema
          <ArrowRight aria-hidden="true" />
        </Button>
      </div>
    </div>
  )
}
