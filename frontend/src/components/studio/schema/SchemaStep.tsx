import { useCallback, useState } from "react"
import { ArrowRight, Network, PanelRightClose, PanelRightOpen } from "lucide-react"
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
  // The side panel starts open on wide screens; on narrower ones the graph gets the full width.
  const [rulesOpen, setRulesOpen] = useState(() => window.matchMedia("(min-width: 1280px)").matches)

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
  const panelOpen = rulesOpen || Boolean(column)

  return (
    // Fixed to the viewport so the graph fills the space between header and bottom bar.
    // min-h keeps it usable when the window is very short or zoomed in (the page scrolls then).
    <div className="flex h-[calc(100dvh-4rem)] min-h-[560px] flex-col">
      <div className="shrink-0 space-y-3 px-4 pt-6 pb-4 md:px-gutter-lg">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="font-heading text-headline-xl font-medium tracking-tight text-ink">Review the schema</h1>
            <p className="tabular mt-1 font-mono text-code-md text-ink-muted">
              {schema.tables.length} tables · {formatInt(columnCount)} columns · {linkCount} links
              {state.rowsSampled ? ` · profiled from ${formatInt(state.rowsSampled)} sample rows` : ""}
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            className="border border-line"
            aria-expanded={panelOpen}
            aria-controls="schema-side-panel"
            onClick={() => {
              if (panelOpen) {
                setRulesOpen(false)
                dispatch({ type: "selectColumn", ref: null })
              } else setRulesOpen(true)
            }}
          >
            {panelOpen ? <PanelRightClose aria-hidden="true" /> : <PanelRightOpen aria-hidden="true" />}
            {panelOpen ? "Hide panel" : `Rules (${schema.rules.length})`}
          </Button>
        </div>
        <NoteBar notes={state.notes} autoAdded={state.autoAdded} />
      </div>

      <div className="flex min-h-0 flex-1 gap-4 px-4 pb-4 md:px-gutter-lg">
        <div className="relative min-h-[260px] min-w-0 flex-1 overflow-hidden rounded-xl border border-line bg-canvas">
          <SchemaGraph schema={schema} selected={selectedColumn} onSelect={onSelect} />
        </div>
        {panelOpen && (
        <aside
          id="schema-side-panel"
          aria-label={column ? "Column details" : "Business rules"}
          className="flex w-[300px] shrink-0 flex-col overflow-hidden rounded-xl border border-line bg-card shadow-sm xl:w-[340px]"
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
        )}
      </div>

      <BottomBar
        sticky={false}
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
