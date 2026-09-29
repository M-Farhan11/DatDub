import { useMemo } from "react"
import { createColumnHelper, tableFeatures, useTable } from "@tanstack/react-table"
import type { Row } from "@/api/types"
import { cn } from "@/lib/utils"

const features = tableFeatures({})
const helper = createColumnHelper<typeof features, Row>()

interface DataGridProps {
  columns: string[]
  /** column name -> true when values are numbers (right-aligned) */
  numeric: Set<string>
  rows: Row[]
  primaryKey: string
  /** IDs changed on purpose by edge cases; their rows get a teal dot */
  affected: Set<string>
  /** row offset for the row-number column */
  offset: number
}

const formatValue = (v: Row[string]) => (v === null ? null : typeof v === "boolean" ? (v ? "true" : "false") : String(v))

export function DataGrid({ columns, numeric, rows, primaryKey, affected, offset }: DataGridProps) {
  const defs = useMemo(
    () =>
      helper.columns(
        columns.map((name) =>
          helper.accessor((row: Row) => row[name] ?? null, {
            id: name,
            header: name,
            cell: (info) => {
              const text = formatValue(info.getValue())
              return text === null ? <span className="text-hint italic">empty</span> : text
            },
          }),
        ),
      ),
    [columns],
  )

  const table = useTable({ features, columns: defs, data: rows })

  return (
    <div className="max-h-[max(300px,calc(100dvh-440px))] overflow-auto rounded-xl border border-line bg-card shadow-sm">
      <table className="w-full border-collapse text-left">
        <thead className="sticky top-0 z-10 bg-surface-low">
          {table.getHeaderGroups().map((group) => (
            <tr key={group.id}>
              <th scope="col" className="w-12 border-b border-line px-3 py-2.5">
                <span className="sr-only">Row</span>
              </th>
              {group.headers.map((header) => (
                <th
                  key={header.id}
                  scope="col"
                  className={cn(
                    "border-b border-line px-3 py-2.5 font-mono text-code-sm font-medium whitespace-nowrap text-ink-muted",
                    numeric.has(header.column.id) && "text-right",
                  )}
                >
                  {header.isPlaceholder ? null : <table.FlexRender header={header} />}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row, i) => {
            const id = String(row.original[primaryKey] ?? "")
            const changed = affected.has(id)
            return (
              <tr key={row.id} className="border-b border-line last:border-b-0 hover:bg-surface-low/60">
                <td className="px-3 py-2 whitespace-nowrap">
                  <span className="flex items-center gap-1.5">
                    <span
                      className={cn("size-2 rounded-full", changed ? "bg-expected" : "bg-transparent")}
                      title={changed ? "Changed on purpose by an edge case" : undefined}
                      aria-hidden="true"
                    />
                    <span className="tabular font-mono text-code-sm text-hint">{offset + i + 1}</span>
                    {changed && <span className="sr-only">Changed on purpose by an edge case</span>}
                  </span>
                </td>
                {row.getAllCells().map((cell) => (
                  <td
                    key={cell.id}
                    className={cn(
                      "tabular max-w-[260px] truncate px-3 py-2 font-mono text-code-sm whitespace-nowrap text-ink",
                      numeric.has(cell.column.id) && "text-right",
                    )}
                  >
                    <table.FlexRender cell={cell} />
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
