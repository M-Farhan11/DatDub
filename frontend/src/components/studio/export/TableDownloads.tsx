import { useState } from "react"
import { Download, Loader2 } from "lucide-react"
import { errorMessage, getTablePage, isApiError } from "@/api/client"
import type { DatasetSchema, Row } from "@/api/types"
import { Card } from "@/components/shared/Card"
import { ErrorCallout } from "@/components/shared/ErrorCallout"
import { MonoText } from "@/components/shared/MonoText"
import { Button } from "@/components/ui/button"
import { downloadBlob, toCsv } from "@/lib/download"
import { formatInt } from "@/lib/format"

const PAGE = 500 // the API's maximum page size

interface TableDownloadsProps {
  datasetId: string
  schema: DatasetSchema
  rowCounts: Record<string, number>
  onExpired: () => void
}

export function TableDownloads({ datasetId, schema, rowCounts, onExpired }: TableDownloadsProps) {
  const [busy, setBusy] = useState<{ table: string; done: number } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const downloadCsv = async (table: string) => {
    setError(null)
    setBusy({ table, done: 0 })
    const columns = schema.tables.find((t) => t.name === table)?.columns.map((c) => c.name) ?? []
    const rows: Row[] = []
    try {
      let total = rowCounts[table] ?? 0
      while (rows.length < total) {
        const page = await getTablePage(datasetId, table, rows.length, PAGE)
        total = page.total
        rows.push(...page.rows)
        setBusy({ table, done: rows.length })
        if (page.rows.length === 0) break
      }
      downloadBlob(`${table}.csv`, toCsv(rows, columns.length ? columns : Object.keys(rows[0] ?? {})), "text/csv")
    } catch (err) {
      if (isApiError(err, "dataset_not_found")) onExpired()
      else setError(errorMessage(err))
    } finally {
      setBusy(null)
    }
  }

  return (
    <Card title="Tables one by one" description="CSV files built in your browser from the generated data." flush>
      <ul className="divide-y divide-line">
        {Object.entries(rowCounts).map(([table, count]) => {
          const active = busy?.table === table
          return (
            <li key={table} className="flex items-center gap-3 px-6 py-3">
              <MonoText className="min-w-0 flex-1 truncate text-ink">{table}</MonoText>
              <MonoText className="text-code-sm text-ink-muted">
                {active ? `${formatInt(busy.done)} of ${formatInt(count)}` : `${formatInt(count)} rows`}
              </MonoText>
              <Button
                size="sm"
                variant="secondary"
                className="border border-line"
                disabled={busy !== null}
                aria-label={`Download ${table} as CSV`}
                onClick={() => void downloadCsv(table)}
              >
                {active ? <Loader2 className="animate-spin" aria-hidden="true" /> : <Download aria-hidden="true" />}
                CSV
              </Button>
            </li>
          )
        })}
      </ul>
      {error && (
        <div className="p-4">
          <ErrorCallout title="The download did not finish" message={error} />
        </div>
      )}
    </Card>
  )
}
