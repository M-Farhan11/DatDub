import { useCallback, useState } from "react"
import { ArrowRight, Table } from "lucide-react"
import { BottomBar } from "@/components/shared/BottomBar"
import { EmptyState } from "@/components/shared/EmptyState"
import { Tabs, type TabItem } from "@/components/shared/Tabs"
import { Button } from "@/components/ui/button"
import type { ResultsTab } from "@/state/studioReducer"
import { useStudio } from "@/state/useStudio"
import { ChecksTab } from "./ChecksTab"
import { DataTab } from "./DataTab"
import { EdgeCasesTab } from "./EdgeCasesTab"
import { ExpiredState } from "./ExpiredState"
import { InvoicesTab } from "./InvoicesTab"
import { ResultsHeader } from "./ResultsHeader"

export function ResultsStep() {
  const { state, dispatch } = useStudio()
  const { schema, result } = state
  const tab = state.resultsTab
  const dataTable = state.dataTable
  const setTab = (next: ResultsTab) => dispatch({ type: "openResults", tab: next })
  const setDataTable = (table: string) => dispatch({ type: "openResults", tab: "data", table })
  const [expired, setExpired] = useState(false)
  const onExpired = useCallback(() => setExpired(true), [])

  if (expired) return <ExpiredState />

  if (!schema || !result) {
    return (
      <div className="mx-auto w-full max-w-[880px] px-gutter-lg pt-16">
        <EmptyState
          icon={Table}
          title="No results yet"
          description="Configure the dataset and generate it to see the checks, data and edge cases here."
          action={<Button onClick={() => dispatch({ type: "goTo", step: "Configure" })}>Go to Configure</Button>}
        />
      </div>
    )
  }

  const hasInvoices = Boolean(schema.document_hints?.invoice)
  const activeTab: ResultsTab = tab === "invoices" && !hasInvoices ? "checks" : tab
  const tables = Object.keys(result.row_counts)
  const activeTable = dataTable && tables.includes(dataTable) ? dataTable : tables[0]
  const items: TabItem<ResultsTab>[] = [
    { id: "checks", label: "Checks", count: result.report.checks.length },
    { id: "data", label: "Data", count: tables.length },
    { id: "edge-cases", label: "Edge cases", count: result.ground_truth.length },
    ...(hasInvoices ? [{ id: "invoices" as const, label: "Invoices" }] : []),
  ]

  return (
    <div className="flex min-h-[calc(100dvh-4rem)] flex-col">
      <div className="mx-auto w-full max-w-[1680px] flex-1 space-y-6 px-4 pt-8 pb-10 md:px-gutter-lg">
        <ResultsHeader name={schema.name} seed={state.generatedWith?.config.seed ?? state.config.seed} result={result} />
        <Tabs label="Results" items={items} value={activeTab} onChange={setTab} idPrefix="results" />
        <div role="tabpanel" id={`results-panel-${activeTab}`} aria-labelledby={`results-tab-${activeTab}`} tabIndex={0}>
          {activeTab === "checks" && <ChecksTab report={result.report} rules={schema.rules} />}
          {activeTab === "data" && activeTable && (
            <DataTab
              key={activeTable}
              schema={schema}
              result={result}
              table={activeTable}
              onTableChange={setDataTable}
              onExpired={onExpired}
            />
          )}
          {activeTab === "edge-cases" && (
            <EdgeCasesTab
              groundTruth={result.ground_truth}
              proposals={state.proposals}
              onViewRows={(table) => setDataTable(table)}
              onAddEdgeCases={() => dispatch({ type: "goTo", step: "Configure" })}
            />
          )}
          {activeTab === "invoices" && hasInvoices && <InvoicesTab datasetId={result.dataset_id} onExpired={onExpired} />}
        </div>
      </div>

      <BottomBar onBack={() => dispatch({ type: "goTo", step: "Configure" })} backLabel="Adjust settings">
        <Button onClick={() => dispatch({ type: "advance", step: "Export" })}>
          Continue to export
          <ArrowRight aria-hidden="true" />
        </Button>
      </BottomBar>
    </div>
  )
}
