import { useRef, type KeyboardEvent } from "react"
import { cn } from "@/lib/utils"

export interface TabItem<T extends string> {
  id: T
  label: string
  /** Small count shown after the label. */
  count?: number
}

interface TabsProps<T extends string> {
  label: string
  items: TabItem<T>[]
  value: T
  onChange: (id: T) => void
  /** id prefix used to link tabs to their panels: `${idPrefix}-panel-${id}` */
  idPrefix: string
}

/** Underlined tab list with arrow-key navigation. Render the panel with `tabPanelProps`. */
export function Tabs<T extends string>({ label, items, value, onChange, idPrefix }: TabsProps<T>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([])

  const onKeyDown = (e: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const delta = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0
    const target = e.key === "Home" ? 0 : e.key === "End" ? items.length - 1 : (index + delta + items.length) % items.length
    if (!delta && e.key !== "Home" && e.key !== "End") return
    e.preventDefault()
    onChange(items[target].id)
    refs.current[target]?.focus()
  }

  return (
    <div role="tablist" aria-label={label} className="flex gap-1 overflow-x-auto border-b border-line">
      {items.map((item, i) => {
        const selected = item.id === value
        return (
          <button
            key={item.id}
            ref={(el) => {
              refs.current[i] = el
            }}
            id={`${idPrefix}-tab-${item.id}`}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-controls={`${idPrefix}-panel-${item.id}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(item.id)}
            onKeyDown={(e) => onKeyDown(e, i)}
            className={cn(
              "relative -mb-px flex h-11 shrink-0 items-center gap-2 border-b-2 px-4 font-heading text-label-lg font-medium transition-colors",
              selected ? "border-primary text-primary-deep" : "border-transparent text-ink-muted hover:text-ink",
            )}
          >
            {item.label}
            {item.count !== undefined && (
              <span
                className={cn(
                  "tabular rounded-full px-1.5 font-mono text-code-sm",
                  selected ? "bg-primary-tint text-primary-deep" : "bg-surface-high text-ink-muted",
                )}
              >
                {item.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
