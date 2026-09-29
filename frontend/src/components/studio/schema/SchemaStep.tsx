import { useCallback } from "react"
import { ArrowRight, Network } from "lucide-react"
import { BottomBar } from "@/components/shared/BottomBar"
import { EmptyState } from "@/components/shared/EmptyState"
import { Button } from "@/components/ui/button"
import { formatInt } from "@/lib/format"
import type { ColumnRef } from "@/state/studioReducer"
import { useStudio } from "@/state/useStudio"
import { ColumnDetails } from "./ColumnDetails"
import { NoteBar } from "./NoteBar"
import { RulesPanel } from "./RulesPanel"
import { SchemaGraph } from "./SchemaGraph"

export function SchemaStep() {
  const { state, dispatch } = useStudio()
  const { schema, selectedColumn } = state
  const onSelect = useCallback((ref: ColumnRef) => dispatch({ type: "selectColumn", ref }), [dispatch])

  if (!schema) {
    return (
      <div className="mx-auto w-full max-w-[880px] px-gutter-lg pt-16">
        <EmptyState
          icon={Network}
          title="No schema yet"
          description="Choose a source first. DatDub reads its structure and shows it here."
          action={<Button onClick={() => dispatch({ type: "openSource", screen: "picker" })}>Choose a source</Button>}
        />
      </div>
    )
  }

  const columnCount = schema.tables.reduce((n, t) => n + t.columns.length, 0)
  const linkCount = schema.tables.reduce((n, t) => n + t.foreign_keys.length, 0)
  const selectedTable = selectedColumn ? schema.tables.find((t) => t.name === selectedColumn.table) : undefined
  const column = selectedTable?.columns.find((c) => c.name === selectedColumn?.column)

  return (
    <div className="flex h-[calc(100dvh-4rem)] flex-col">
      <div className="space-y-3 px-4 pt-6 pb-4 md:px-gutter-lg">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="font-heading text-headline-xl font-medium tracking-tight text-ink">Review the schema</h1>
            <p className="tabular mt-1 font-mono text-code-md text-ink-muted">
              {schema.tables.length} tables · {formatInt(columnCount)} columns · {linkCount} links
              {state.rowsSampled ? ` · profiled from ${formatInt(state.rowsSampled)} sample rows` : ""}
            </p>
          </div>
        </div>
        <NoteBar notes={state.notes} autoAdded={state.autoAdded} />
      </div>

      <div className="flex min-h-0 flex-1 gap-4 px-4 pb-4 md:px-gutter-lg">
        <div className="relative min-h-[420px] min-w-0 flex-1 overflow-hidden rounded-xl border border-line bg-canvas">
          <SchemaGraph schema={schema} selected={selectedColumn} onSelect={onSelect} />
        </div>
        <aside
          aria-label={column ? "Column details" : "Business rules"}
          className="w-[340px] shrink-0 overflow-hidden rounded-xl border border-line bg-card shadow-sm"
        >
          {selectedTable && column ? (
            <ColumnDetails
              key={`${selectedTable.name}.${column.name}`}
              table={selectedTable}
              column={column}
              onSave={(patch) =>
                dispatch({ type: "updateColumn", ref: { table: selectedTable.name, column: column.name }, patch })
              }
              onClose={() => dispatch({ type: "selectColumn", ref: null })}
            />
          ) : (
            <RulesPanel rules={schema.rules} />
          )}
        </aside>
      </div>

      <BottomBar
        onBack={() => dispatch({ type: "openSource", screen: "picker" })}
        backLabel="Change source"
        summary="Changes here apply to the next generation."
      >
        <Button onClick={() => dispatch({ type: "advance", step: "Configure" })}>
          Continue
          <ArrowRight aria-hidden="true" />
        </Button>
      </BottomBar>
    </div>
  )
}
