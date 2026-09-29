import { Calendar, Hash, ToggleLeft, Type } from "lucide-react"
import type { DataType } from "@/api/types"

const ICONS = {
  string: Type,
  integer: Hash,
  float: Hash,
  decimal: Hash,
  boolean: ToggleLeft,
  date: Calendar,
  datetime: Calendar,
} satisfies Record<DataType, typeof Type>

export function ColumnTypeIcon({ type, className }: { type: DataType; className?: string }) {
  const Icon = ICONS[type]
  return <Icon className={className} aria-hidden="true" />
}
