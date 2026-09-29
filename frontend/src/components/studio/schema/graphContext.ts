import { createContext, useContext } from "react"
import type { TableSchema } from "@/api/types"
import type { ColumnRef } from "@/state/studioReducer"

export interface SchemaGraphContextValue {
  tables: Map<string, TableSchema>
  selected: ColumnRef | null
  onSelect: (ref: ColumnRef) => void
}

/**
 * Nodes read table data and selection from here instead of node data, so
 * editing a column or selecting one never resets dragged node positions.
 */
export const SchemaGraphContext = createContext<SchemaGraphContextValue | null>(null)

export function useSchemaGraph(): SchemaGraphContextValue {
  const ctx = useContext(SchemaGraphContext)
  if (!ctx) throw new Error("useSchemaGraph must be used inside SchemaGraphContext")
  return ctx
}
