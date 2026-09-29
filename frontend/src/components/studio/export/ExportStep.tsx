import { useCallback, useState } from "react"
import { Clock, PackageOpen } from "lucide-react"
import { BottomBar } from "@/components/shared/BottomBar"
import { EmptyState } from "@/components/shared/EmptyState"
import { PageHeader } from "@/components/shared/PageHeader"
import { Button } from "@/components/ui/button"
import { useStudio } from "@/state/useStudio"
import { ExpiredState } from "../results/ExpiredState"
import { RecreateCard } from "./RecreateCard"
import { StartOverButton } from "./StartOverButton"
import { TableDownloads } from "./TableDownloads"
import { ZipDownloadCard } from "./ZipDownloadCard"

export function ExportStep() {
  const { state, dispatch } = useStudio()
  const { schema, result } = state
  const [expired, setExpired] = useState(false)
  const onExpired = useCallback(() => setExpired(true), [])

  if (expired) return <ExpiredState />

  if (!schema || !result) {
    return (
      <div className="mx-auto w-full max-w-[880px] px-gutter-lg pt-16">
        <EmptyState
          icon={PackageOpen}
          title="Nothing to export yet"
          description="Generate a dataset first, then download it here."
          action={<Button onClick={() => dispatch({ type: "goTo", step: "Configure" })}>Go to Configure</Button>}
        />
      </div>
    )
  }

  return (
    <div className="flex min-h-[calc(100dvh-4rem)] flex-col">
      <div className="mx-auto w-full max-w-[1100px] flex-1 space-y-6 px-4 pt-8 pb-10 md:px-gutter-lg">
        <PageHeader
          title="Your dataset is ready"
          subtitle={
            <span className="inline-flex items-center gap-2">
              <Clock className="size-4 shrink-0" aria-hidden="true" />
              This dataset is deleted after 60 minutes. Download what you need.
            </span>
          }
        />
        <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
          <ZipDownloadCard
            datasetId={result.dataset_id}
            name={schema.name}
            hasInvoices={Boolean(schema.document_hints?.invoice)}
            onExpired={onExpired}
          />
          <TableDownloads datasetId={result.dataset_id} schema={schema} rowCounts={result.row_counts} onExpired={onExpired} />
        </div>
        <RecreateCard
          schemaName={schema.name}
          config={state.generatedWith?.config ?? state.config}
          scenarios={state.generatedWith?.scenarios ?? []}
        />
      </div>

      <BottomBar onBack={() => dispatch({ type: "goTo", step: "Results" })} backLabel="Back to results">
        <StartOverButton onConfirm={() => dispatch({ type: "reset" })} />
      </BottomBar>
    </div>
  )
}
