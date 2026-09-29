import type { DbTableInfo } from "@/api/types"
import { MonoText } from "@/components/shared/MonoText"
import { formatInt } from "@/lib/format"
import { cn } from "@/lib/utils"

interface DbTablePickerProps {
  tables: DbTableInfo[]
  chosen: Set<string>
  /** parent table -> child that needs it */
  autoAdded: Map<string, string>
  onToggle: (name: string, checked: boolean) => void
  disabled?: boolean
}

export function DbTablePicker({ tables, chosen, autoAdded, onToggle, disabled }: DbTablePickerProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-line">
      <table className="w-full min-w-[560px] border-collapse text-left">
        <caption className="sr-only">Tables found in the database</caption>
        <thead className="bg-surface-low">
          <tr className="font-heading text-label-md text-ink-muted">
            <th scope="col" className="w-12 px-4 py-2.5">
              <span className="sr-only">Include</span>
            </th>
            <th scope="col" className="px-2 py-2.5 font-medium">Table</th>
            <th scope="col" className="px-2 py-2.5 text-right font-medium">Columns</th>
            <th scope="col" className="px-2 py-2.5 text-right font-medium">Rows</th>
            <th scope="col" className="px-4 py-2.5 font-medium">Linked to</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {tables.map((table) => {
            const isChosen = chosen.has(table.name)
            const neededBy = autoAdded.get(table.name)
            const checked = isChosen || neededBy !== undefined
            const id = `db-table-${table.name}`
            return (
              <tr key={table.name} className={cn("bg-card", checked && "bg-surface-low/60")}>
                <td className="px-4 py-3">
                  <input
                    id={id}
                    type="checkbox"
                    checked={checked}
                    disabled={disabled || neededBy !== undefined}
                    onChange={(e) => onToggle(table.name, e.target.checked)}
                    title={neededBy ? `Needed by ${neededBy}` : undefined}
                    className="size-4 cursor-pointer accent-[var(--primary)] disabled:cursor-not-allowed"
                  />
                </td>
                <td className="px-2 py-3">
                  <label htmlFor={id} className="flex flex-wrap items-center gap-2">
                    <MonoText className="text-ink">{table.name}</MonoText>
                    {neededBy && (
                      <span className="rounded-full bg-primary-tint px-2 py-0.5 font-heading text-label-md font-medium text-primary-deep">
                        added automatically
                      </span>
                    )}
                  </label>
                  {neededBy && <p className="mt-0.5 text-body-sm text-ink-muted">Needed by {neededBy}</p>}
                </td>
                <td className="px-2 py-3 text-right">
                  <MonoText className="text-ink-muted">{table.column_count}</MonoText>
                </td>
                <td className="px-2 py-3 text-right">
                  <MonoText className="text-ink-muted">~{formatInt(table.estimated_rows)}</MonoText>
                </td>
                <td className="px-4 py-3">
                  {table.references.length > 0 ? (
                    <MonoText className="text-ink-muted">{table.references.join(", ")}</MonoText>
                  ) : (
                    <span className="text-body-sm text-hint">None</span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
