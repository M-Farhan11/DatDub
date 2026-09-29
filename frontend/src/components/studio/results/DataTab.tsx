import { useEffect, useMemo, useState } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { errorMessage, getTablePage, isApiError } from "@/api/client"
import type { DatasetSchema, GenerateResponse, Row } from "@/api/types"
import { ErrorCallout } from "@/components/shared/ErrorCallout"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { MonoText } from "@/components/shared/MonoText"
import { Button } from "@/components/ui/button"
import { formatInt } from "@/lib/format"
import { cn } from "@/lib/utils"
import { DataGrid } from "./DataGrid"

const PAGE_SIZE = 50
const NUMERIC = new Set(["integer", "float", "decimal"])

interface DataTabProps {
  schema: DatasetSchema
  result: GenerateResponse
  table: string
  onTableChange: (table: string) => void
  onExpired: () => void
}

export function DataTab({ schema, result, table, onTableChange, onExpired }: DataTabProps) {
  const [page, setPage] = useState(0)
  /** Last fetched page (pages after the first); the first page comes from the previews. */
  const [fetched, setFetched] = useState<{ page: number; attempt: number; rows: Row[] } | null>(null)
  const [failure, setFailure] = useState<{ page: number; attempt: number; message: string } | null>(null)
  const [attempt, setAttempt] = useState(0)

  const tableSchema = schema.tables.find((t) => t.name === table)
  const total = result.row_counts[table] ?? 0
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const offset = page * PAGE_SIZE

  const columns = useMemo(
    () => tableSchema?.columns.map((c) => c.name) ?? Object.keys(result.previews[table]?.[0] ?? {}),
    [tableSchema, result.previews, table],
  )
  const numeric = useMemo(
    () => new Set(tableSchema?.columns.filter((c) => NUMERIC.has(c.data_type)).map((c) => c.name) ?? []),
    [tableSchema],
  )
  const affected = useMemo(
    () => new Set(result.ground_truth.filter((g) => g.table === table).flatMap((g) => g.affected_ids)),
    [result.ground_truth, table],
  )

  // Later pages are fetched; loading/error are derived from which page has arrived.
  useEffect(() => {
    if (page === 0) return
    let alive = true
    getTablePage(result.dataset_id, table, offset, PAGE_SIZE)
      .then((res) => alive && setFetched({ page, attempt, rows: res.rows }))
      .catch((err: unknown) => {
        if (!alive) return
        if (isApiError(err, "dataset_not_found")) onExpired()
        else setFailure({ page, attempt, message: errorMessage(err) })
      })
    return () => {
      alive = false
    }
  }, [page, table, offset, result.dataset_id, attempt, onExpired])

  const error = page > 0 && failure?.page === page && failure.attempt === attempt ? failure.message : null
  const ready = page === 0 || (fetched?.page === page && fetched.attempt === attempt)
  const loading = !ready && !error
  const rows = page === 0 ? (result.previews[table] ?? []) : ready && fetched ? fetched.rows : []

  const selectTable = (name: string) => onTableChange(name)

  const tables = Object.keys(result.row_counts)

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
      <nav aria-label="Tables">
        <ul className="space-y-1">
          {tables.map((name) => (
            <li key={name}>
              <button
                type="button"
                onClick={() => selectTable(name)}
                aria-current={name === table ? "true" : undefined}
                className={cn(
                  "flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left transition-colors",
                  name === table ? "bg-primary-tint text-primary-deep" : "text-ink hover:bg-surface-low",
                )}
              >
                <MonoText className="truncate">{name}</MonoText>
                <MonoText className="text-code-sm text-ink-muted">{formatInt(result.row_counts[name])}</MonoText>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="min-w-0 space-y-3">
        {error ? (
          <ErrorCallout
            title="These rows could not be loaded"
            message={error}
            action={
              <Button size="sm" variant="secondary" className="border border-line" onClick={() => setAttempt((n) => n + 1)}>
                Try again
              </Button>
            }
          />
        ) : loading ? (
          <div className="rounded-xl border border-line bg-card p-4">
            <LoadingSkeleton lines={8} lineClassName="h-6" label="Loading rows" />
          </div>
        ) : (
          <DataGrid
            columns={columns}
            numeric={numeric}
            rows={rows}
            primaryKey={tableSchema?.primary_key ?? columns[0] ?? ""}
            affected={affected}
            offset={offset}
          />
        )}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="tabular text-body-sm text-ink-muted">
            Showing {total === 0 ? 0 : formatInt(offset + 1)}–{formatInt(Math.min(total, offset + PAGE_SIZE))} of{" "}
            {formatInt(total)} rows
            {affected.size > 0 && (
              <span className="ml-3 inline-flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-expected" aria-hidden="true" />
                changed on purpose
              </span>
            )}
          </p>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" disabled={page === 0 || loading} onClick={() => setPage((p) => p - 1)}>
              <ChevronLeft aria-hidden="true" />
              Previous
            </Button>
            <span className="tabular font-mono text-code-sm text-ink-muted">
              {page + 1} / {formatInt(pages)}
            </span>
            <Button variant="ghost" size="sm" disabled={page >= pages - 1 || loading} onClick={() => setPage((p) => p + 1)}>
              Next
              <ChevronRight aria-hidden="true" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
