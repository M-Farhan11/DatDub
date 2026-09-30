import { useEffect, useMemo, useState } from "react"
import { FileText } from "lucide-react"
import { errorMessage, fetchFile, invoicePdfUrl, isApiError, listInvoices } from "@/api/client"
import { EmptyState } from "@/components/shared/EmptyState"
import { ErrorCallout } from "@/components/shared/ErrorCallout"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { formatInt } from "@/lib/format"
import { textInputClass } from "@/lib/styles"
import { ChipStrip } from "./ChipStrip"

type Preview =
  | { kind: "loading" }
  | { kind: "ready"; url: string }
  | { kind: "coming-soon" }
  | { kind: "error"; message: string }

const LIST_LIMIT = 100

interface InvoicesTabProps {
  datasetId: string
  onExpired: () => void
}

export function InvoicesTab({ datasetId, onExpired }: InvoicesTabProps) {
  const [ids, setIds] = useState<string[] | null>(null)
  const [listError, setListError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  /** Outcome for one invoice id; anything else means that invoice is still loading. */
  const [query, setQuery] = useState("")
  const [outcome, setOutcome] = useState<{ id: string; preview: Preview } | null>(null)

  useEffect(() => {
    let alive = true
    listInvoices(datasetId)
      .then((res) => {
        if (!alive) return
        setIds(res.invoice_ids)
        setSelected(res.invoice_ids[0] ?? null)
      })
      .catch((err: unknown) => {
        if (!alive) return
        if (isApiError(err, "dataset_not_found")) onExpired()
        else setListError(errorMessage(err))
      })
    return () => {
      alive = false
    }
  }, [datasetId, onExpired])

  // The PDF is fetched first so a 501 (not built yet) shows a placeholder, not a broken frame.
  useEffect(() => {
    if (!selected) return
    let alive = true
    let objectUrl: string | null = null
    const id = selected
    fetchFile(invoicePdfUrl(datasetId, id))
      .then((blob) => {
        if (!alive) return
        objectUrl = URL.createObjectURL(blob)
        setOutcome({ id, preview: { kind: "ready", url: objectUrl } })
      })
      .catch((err: unknown) => {
        if (!alive) return
        if (isApiError(err, "not_implemented")) setOutcome({ id, preview: { kind: "coming-soon" } })
        else if (isApiError(err, "dataset_not_found")) onExpired()
        else setOutcome({ id, preview: { kind: "error", message: errorMessage(err) } })
      })
    return () => {
      alive = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [datasetId, selected, onExpired])

  // A dataset can hold tens of thousands of invoices: filter by ID and render at most LIST_LIMIT.
  const matches = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (ids ?? []).filter((id) => !q || id.toLowerCase().includes(q))
  }, [ids, query])
  const shown = matches.slice(0, LIST_LIMIT)

  const preview: Preview = outcome && outcome.id === selected ? outcome.preview : { kind: "loading" }

  if (listError) return <ErrorCallout title="Invoices could not be listed" message={listError} />
  if (ids === null) return <LoadingSkeleton lines={6} lineClassName="h-9" label="Loading invoices" />
  if (ids.length === 0) {
    return <EmptyState icon={FileText} title="No invoices in this dataset" description="Generate more rows to get invoices." />
  }

  return (
    <div className="space-y-4">
      <ChipStrip
        label="Invoices"
        items={shown.map((id) => ({ id, label: id }))}
        value={selected}
        onChange={setSelected}
        lead={
          <>
            <label htmlFor="invoice-search" className="sr-only">
              Find an invoice by ID
            </label>
            <input
              id="invoice-search"
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Find INV-00042"
              className={`${textInputClass} font-mono text-code-md`}
            />
          </>
        }
        trail={
          <span className="tabular" aria-live="polite">
            {matches.length === 0
              ? "No invoice matches that ID."
              : matches.length > LIST_LIMIT
                ? `${LIST_LIMIT} of ${formatInt(matches.length)}`
                : `${formatInt(matches.length)} ${matches.length === 1 ? "invoice" : "invoices"}`}
          </span>
        }
      />

      <div className="min-w-0">
        {preview.kind === "loading" && (
          <div className="rounded-xl border border-line bg-card p-6">
            <LoadingSkeleton lines={10} lineClassName="h-5" label="Loading invoice" />
          </div>
        )}
        {preview.kind === "ready" && (
          <iframe
            title={`Invoice ${selected ?? ""}`}
            src={preview.url}
            className="h-[max(560px,calc(100dvh-330px))] w-full rounded-xl border border-line bg-card shadow-sm"
          />
        )}
        {preview.kind === "coming-soon" && (
          <EmptyState
            icon={FileText}
            title="Invoice preview is coming soon"
            description="Invoice PDFs are not available yet. The invoice data is already in the Data tab."
          />
        )}
        {preview.kind === "error" && <ErrorCallout title="This invoice could not be shown" message={preview.message} />}
      </div>
    </div>
  )
}
