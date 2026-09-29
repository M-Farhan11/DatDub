import { useState } from "react"
import { ArrowRight, SlidersHorizontal } from "lucide-react"
import { errorMessage, generate } from "@/api/client"
import { BottomBar } from "@/components/shared/BottomBar"
import { EmptyState } from "@/components/shared/EmptyState"
import { ErrorCallout } from "@/components/shared/ErrorCallout"
import { PageHeader } from "@/components/shared/PageHeader"
import { Button } from "@/components/ui/button"
import { formatInt } from "@/lib/format"
import { rootTables } from "@/state/studioReducer"
import { useStudio } from "@/state/useStudio"
import { EdgeCasesCard } from "./EdgeCasesCard"
import { rowsError } from "./estimates"
import { GeneratingCard } from "./GeneratingCard"
import { SizeSettingsCard } from "./SizeSettingsCard"

export function ConfigureStep() {
  const { state, dispatch, selections } = useStudio()
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { schema, config } = state

  if (!schema) {
    return (
      <div className="mx-auto w-full max-w-[880px] px-gutter-lg pt-16">
        <EmptyState
          icon={SlidersHorizontal}
          title="Nothing to configure yet"
          description="Choose a source and review its schema first."
          action={<Button onClick={() => dispatch({ type: "openSource", screen: "picker" })}>Choose a source</Button>}
        />
      </div>
    )
  }

  const roots = rootTables(schema)
  const invalid = roots.some((t) => rowsError(config.rows[t.name]) !== null)
  const records = selections.reduce((n, s) => n + s.count, 0)
  const rootSummary = roots.map((t) => `${formatInt(config.rows[t.name] || 0)} ${t.name}`).join(", ")
  const edgeLabel = `${selections.length} edge ${selections.length === 1 ? "case" : "cases"}`

  const run = async () => {
    setGenerating(true)
    setError(null)
    try {
      const rows = Object.fromEntries(roots.map((t) => [t.name, config.rows[t.name]]))
      const result = await generate({
        schema,
        rows,
        seed: config.seed,
        null_rate: config.null_rate,
        outlier_rate: config.outlier_rate,
        locale: config.locale,
        scenarios: selections,
      })
      dispatch({ type: "generated", result, config: { ...config, rows }, scenarios: selections })
    } catch (err) {
      setError(errorMessage(err))
      setGenerating(false)
    }
  }

  if (generating) {
    return <GeneratingCard name={schema.name} summary={`seed ${config.seed} · ${rootSummary} · ${edgeLabel}`} />
  }

  return (
    <div className="flex min-h-[calc(100dvh-4rem)] flex-col">
      <div className="mx-auto w-full max-w-[1280px] flex-1 px-4 pt-8 pb-10 md:px-gutter-lg">
        <PageHeader
          title="Configure the data"
          subtitle="Choose the size and settings, then add edge cases to test against."
        />
        {error && <ErrorCallout className="mt-6" title="Generation did not finish" message={error} />}
        <div className="mt-8 grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
          <SizeSettingsCard
            schema={schema}
            config={config}
            onRowsChange={(table, count) => dispatch({ type: "setRows", table, count })}
            onConfigChange={(patch) => dispatch({ type: "setConfig", patch })}
          />
          <EdgeCasesCard
            schema={schema}
            instruction={state.instruction}
            onInstructionChange={(instruction) => dispatch({ type: "setInstruction", instruction })}
            proposals={state.proposals}
            onProposals={(proposals) => dispatch({ type: "setProposals", proposals })}
            selected={state.selectedScenarios}
            onToggle={(id, on) => dispatch({ type: "toggleScenario", id, on })}
            onCountChange={(id, count) => dispatch({ type: "setScenarioCount", id, count })}
          />
        </div>
      </div>

      <BottomBar
        onBack={() => dispatch({ type: "goTo", step: "Schema" })}
        summary={
          <span className="tabular">
            {rootSummary}, {edgeLabel} ({formatInt(records)} records), seed {config.seed}
          </span>
        }
      >
        <Button onClick={run} disabled={invalid} title={invalid ? "Fix the row counts first" : undefined}>
          Generate data
          <ArrowRight aria-hidden="true" />
        </Button>
      </BottomBar>
    </div>
  )
}
