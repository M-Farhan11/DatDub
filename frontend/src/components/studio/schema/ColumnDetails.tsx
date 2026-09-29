import { useState } from "react"
import { Check, ShieldCheck, X } from "lucide-react"
import type { ColumnSchema, SemanticType, TableSchema } from "@/api/types"
import { Field } from "@/components/shared/Field"
import { MonoText } from "@/components/shared/MonoText"
import { Toggle } from "@/components/shared/Toggle"
import { Button } from "@/components/ui/button"
import { humanize } from "@/lib/format"
import { textInputClass } from "@/lib/styles"
import { ConfidenceMeter } from "./ConfidenceMeter"
import { NodeTag } from "./NodeTag"
import { ProfileSummary } from "./ProfileSummary"
import { SEMANTIC_TYPES } from "./schemaText"

type Draft = Pick<ColumnSchema, "semantic_type" | "pii" | "nullable" | "unique">

const draftOf = (c: ColumnSchema): Draft => ({
  semantic_type: c.semantic_type,
  pii: c.pii,
  nullable: c.nullable,
  unique: c.unique,
})

interface ColumnDetailsProps {
  table: TableSchema
  column: ColumnSchema
  onSave: (patch: Draft) => void
  onClose: () => void
}

/** Right panel for the selected column. Mount with a key per column so the draft resets. */
export function ColumnDetails({ table, column, onSave, onClose }: ColumnDetailsProps) {
  const [draft, setDraft] = useState<Draft>(() => draftOf(column))
  const [saved, setSaved] = useState(false)
  const original = draftOf(column)
  const dirty = (Object.keys(draft) as (keyof Draft)[]).some((k) => draft[k] !== original[k])
  const fk = table.foreign_keys.find((f) => f.column === column.name)
  const isPk = column.name === table.primary_key
  const idBase = `col-${table.name}-${column.name}`

  const update = (patch: Partial<Draft>) => {
    setSaved(false)
    setDraft((d) => ({ ...d, ...patch }))
  }

  return (
    <div className="flex h-full flex-col" onKeyDown={(e) => e.key === "Escape" && onClose()}>
      <header className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
        <div className="min-w-0">
          <p className="text-body-sm text-ink-muted">Column details</p>
          <div className="mt-0.5 flex flex-wrap items-center gap-2">
            <MonoText className="text-headline-sm font-medium text-ink">{column.name}</MonoText>
            {isPk && <NodeTag tone="pk">PK</NodeTag>}
            {fk && <NodeTag tone="fk">FK</NodeTag>}
            {draft.pii && <NodeTag tone="pii">PII</NodeTag>}
          </div>
          <p className="mt-1 text-body-sm text-ink-muted">
            in <MonoText className="text-code-sm">{table.name}</MonoText>
            {fk && (
              <>
                {" "}
                · links to <MonoText className="text-code-sm">{fk.ref_table}.{fk.ref_column}</MonoText>
              </>
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close column details"
          className="flex size-8 shrink-0 items-center justify-center rounded-full text-ink-muted hover:bg-surface-low hover:text-ink"
        >
          <X className="size-4" aria-hidden="true" />
        </button>
      </header>

      <div className="flex-1 space-y-6 overflow-y-auto px-5 py-5">
        <ConfidenceMeter value={column.confidence} />

        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <span className="font-heading text-label-lg font-medium text-ink">Data type</span>
            <MonoText className="flex h-10 items-center rounded-lg border border-line bg-surface-low px-3 text-ink-muted">
              {column.data_type}
            </MonoText>
          </div>
          <Field id={`${idBase}-semantic`} label="Meaning">
            <select
              id={`${idBase}-semantic`}
              value={draft.semantic_type}
              onChange={(e) => update({ semantic_type: e.target.value as SemanticType })}
              className={textInputClass}
            >
              {SEMANTIC_TYPES.map((t) => (
                <option key={t} value={t}>
                  {humanize(t)}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <div className="space-y-4">
          <Toggle
            id={`${idBase}-pii`}
            label="Personal data (PII)"
            description="Always replaced with new fake values."
            checked={draft.pii}
            onChange={(pii) => update({ pii })}
          />
          <Toggle
            id={`${idBase}-nullable`}
            label="Can be empty"
            description="Allows empty values in generated rows."
            checked={draft.nullable}
            onChange={(nullable) => update({ nullable })}
            disabled={isPk}
          />
          <Toggle
            id={`${idBase}-unique`}
            label="Unique"
            description="No two rows share a value."
            checked={draft.unique}
            onChange={(unique) => update({ unique })}
            disabled={isPk}
          />
        </div>

        {column.profile && (
          <div>
            <p className="mb-3 font-heading text-label-lg font-medium text-ink">From your sample</p>
            <ProfileSummary profile={column.profile} />
          </div>
        )}

        <p className="flex items-start gap-2 rounded-lg bg-surface-low px-3 py-2.5 text-body-sm text-ink-muted">
          <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary-deep" aria-hidden="true" />
          Real values are never copied. New fake values are generated.
        </p>
      </div>

      <footer className="flex items-center justify-end gap-3 border-t border-line px-5 py-3">
        <span aria-live="polite" className="mr-auto text-body-sm text-pass">
          {saved && (
            <span className="inline-flex items-center gap-1">
              <Check className="size-4" aria-hidden="true" />
              Saved
            </span>
          )}
        </span>
        <Button variant="ghost" size="sm" disabled={!dirty} onClick={() => update(original)}>
          Reset
        </Button>
        <Button
          size="sm"
          disabled={!dirty}
          onClick={() => {
            onSave(draft)
            setSaved(true)
          }}
        >
          Save
        </Button>
      </footer>
    </div>
  )
}
