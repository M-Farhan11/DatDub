import { Handle, Position, type Node, type NodeProps } from "@xyflow/react"
import { formatInt } from "@/lib/format"
import { cn } from "@/lib/utils"
import { ColumnTypeIcon } from "./ColumnTypeIcon"
import { NodeTag as Tag } from "./NodeTag"
import { NODE_WIDTH } from "./graphLayout"
import { useSchemaGraph } from "./graphContext"

export type TableNodeType = Node<{ tableName: string }, "table">

const handleClass = "!size-1.5 !min-h-0 !min-w-0 !border-0 !bg-primary opacity-0"

export function TableNode({ data }: NodeProps<TableNodeType>) {
  const { tables, selected, onSelect } = useSchemaGraph()
  const table = tables.get(data.tableName)
  if (!table) return null

  const fkColumns = new Set(table.foreign_keys.map((fk) => fk.column))
  const hasSelection = selected?.table === table.name

  return (
    <div
      style={{ width: NODE_WIDTH }}
      className={cn(
        "overflow-hidden rounded-xl border bg-card shadow-md transition-[border-color,box-shadow]",
        hasSelection ? "border-primary ring-2 ring-primary/25" : "border-line",
      )}
    >
      <div className="flex h-12 items-center justify-between gap-2 border-b border-line bg-surface-low px-4">
        <span className="truncate font-mono text-code-md font-medium text-ink">{table.name}</span>
        <span className="tabular shrink-0 font-mono text-code-sm text-hint">
          {table.row_count_hint ? `${formatInt(table.row_count_hint)} rows` : "rows from links"}
        </span>
      </div>
      <ul className="py-1.5">
        {table.columns.map((col) => {
          const isPk = col.name === table.primary_key
          const isFk = fkColumns.has(col.name)
          const isSelected = hasSelection && selected?.column === col.name
          return (
            <li key={col.name} className="relative">
              <Handle id={`${col.name}-in`} type="target" position={Position.Left} className={handleClass} isConnectable={false} />
              <button
                type="button"
                aria-pressed={isSelected}
                aria-label={`${table.name}.${col.name}, ${col.data_type}${isPk ? ", primary key" : ""}${isFk ? ", foreign key" : ""}${col.pii ? ", personal data" : ""}`}
                onClick={() => onSelect({ table: table.name, column: col.name })}
                className={cn(
                  "nodrag nopan flex h-8 w-full items-center gap-2 px-4 text-left transition-colors",
                  isSelected ? "bg-primary-tint" : "hover:bg-surface-low",
                )}
              >
                <ColumnTypeIcon type={col.data_type} className="size-3.5 shrink-0 text-hint" />
                <span
                  className={cn(
                    "min-w-0 flex-1 truncate font-mono text-code-sm",
                    isPk ? "font-medium text-primary-deep" : isFk ? "font-medium text-primary" : "text-ink",
                  )}
                >
                  {col.name}
                </span>
                {isPk && <Tag tone="pk">PK</Tag>}
                {isFk && <Tag tone="fk">FK</Tag>}
                {col.pii && <Tag tone="pii">PII</Tag>}
                <span className="shrink-0 font-mono text-code-sm text-hint">{col.data_type}</span>
              </button>
              <Handle id={`${col.name}-out`} type="source" position={Position.Right} className={handleClass} isConnectable={false} />
            </li>
          )
        })}
      </ul>
    </div>
  )
}
