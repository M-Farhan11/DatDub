import { useState } from "react"
import { Download, Info } from "lucide-react"
import { errorMessage, exportZipUrl, fetchFile, isApiError } from "@/api/client"
import { Card } from "@/components/shared/Card"
import { ErrorCallout } from "@/components/shared/ErrorCallout"
import { SubmitButton } from "@/components/shared/SubmitButton"
import { downloadBlob } from "@/lib/download"

const CONTENTS = [
  "Every table as CSV and JSON",
  "schema.json",
  "validation_report.json",
  "ground_truth.json (the answer key)",
]

interface ZipDownloadCardProps {
  datasetId: string
  name: string
  hasInvoices: boolean
  onExpired: () => void
}

export function ZipDownloadCard({ datasetId, name, hasInvoices, onExpired }: ZipDownloadCardProps) {
  const [loading, setLoading] = useState(false)
  const [comingSoon, setComingSoon] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const download = async () => {
    setLoading(true)
    setError(null)
    try {
      const blob = await fetchFile(exportZipUrl(datasetId))
      downloadBlob(`${name}.zip`, blob)
    } catch (err) {
      if (isApiError(err, "not_implemented")) setComingSoon(true)
      else if (isApiError(err, "dataset_not_found")) onExpired()
      else setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="Everything in one file" description="A ZIP with the data, the schema, the checks and the answer key.">
      <ul className="space-y-1.5 text-body-md text-ink-muted">
        {[...CONTENTS, ...(hasInvoices ? ["Up to 20 invoice PDFs"] : [])].map((item) => (
          <li key={item} className="flex items-center gap-2">
            <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" />
            {item}
          </li>
        ))}
      </ul>
      <SubmitButton size="xl" className="mt-6 w-full sm:w-auto" loading={loading} loadingLabel="Preparing the ZIP…" onClick={download}>
        <Download aria-hidden="true" />
        Download ZIP
      </SubmitButton>
      {comingSoon && (
        <p role="status" className="mt-4 flex items-start gap-2 rounded-lg bg-surface-low px-3 py-2.5 text-body-md text-ink-muted">
          <Info className="mt-0.5 size-4 shrink-0 text-primary-deep" aria-hidden="true" />
          ZIP export is coming soon. Download the tables one by one below in the meantime.
        </p>
      )}
      {error && <ErrorCallout className="mt-4" title="The ZIP could not be downloaded" message={error} />}
    </Card>
  )
}
