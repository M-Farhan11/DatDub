import type { ReactElement } from "react"
import { ChevronLeft, ChevronRight, FileText, Network, Table, type LucideIcon } from "lucide-react"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Logo } from "@/components/Logo"
import { cn } from "@/lib/utils"

type Workspace = "tabular" | "relational" | "documents"

const ITEMS: { id: Workspace; label: string; icon: LucideIcon }[] = [
  { id: "tabular", label: "Tabular", icon: Table },
  { id: "relational", label: "Relational", icon: Network },
  { id: "documents", label: "Documents", icon: FileText },
]

interface SidebarProps {
  expanded: boolean
  onToggle: () => void
  onHome: () => void
  active?: Workspace
}

/** Shows a tooltip only while the sidebar is collapsed (labels are visible otherwise). */
function WithTooltip({ show, label, children }: { show: boolean; label: string; children: ReactElement }) {
  if (!show) return children
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side="right">{label}</TooltipContent>
    </Tooltip>
  )
}

export function Sidebar({ expanded, onToggle, onHome, active = "relational" }: SidebarProps) {
  return (
    <aside
      className={cn(
        "fixed top-0 left-0 z-50 flex h-dvh flex-col justify-between border-r border-line bg-card py-4 transition-[width] duration-200 ease-out",
        expanded ? "w-52 shadow-lg md:shadow-none" : "w-16"
      )}
    >
      <div className="flex w-full flex-col gap-6 px-3">
        <WithTooltip show={!expanded} label="Back to home">
          <button
            type="button"
            onClick={onHome}
            aria-label="DatDub home"
            className="flex h-10 items-center rounded-lg px-0.5 transition-opacity hover:opacity-90"
          >
            <Logo size={36} withText={expanded} textClassName="text-headline-sm" />
          </button>
        </WithTooltip>

        <nav aria-label="Workspace" className="flex flex-col gap-2">
          {ITEMS.map(({ id, label, icon: Icon }) => {
            const isActive = id === active
            return (
              <WithTooltip key={id} show={!expanded} label={label}>
                <button
                  type="button"
                  aria-label={expanded ? undefined : label}
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "flex h-11 items-center gap-3 rounded-xl px-3 transition-colors",
                    isActive
                      ? "bg-surface-high text-primary-deep"
                      : "text-ink-muted hover:bg-surface-high hover:text-ink"
                  )}
                >
                  <Icon className="size-[22px] shrink-0" aria-hidden="true" />
                  {expanded && <span className="font-heading text-label-lg font-medium">{label}</span>}
                </button>
              </WithTooltip>
            )
          })}
        </nav>
      </div>

      <div className="flex w-full px-3">
        <WithTooltip show={!expanded} label="Expand navigation">
          <button
            type="button"
            onClick={onToggle}
            aria-label={expanded ? "Collapse navigation" : "Expand navigation"}
            aria-expanded={expanded}
            className={cn(
              "flex h-11 items-center gap-3 rounded-xl px-3 text-ink-muted transition-colors hover:bg-surface-high hover:text-ink",
              expanded && "w-full"
            )}
          >
            {expanded ? (
              <ChevronLeft className="size-5 shrink-0" aria-hidden="true" />
            ) : (
              <ChevronRight className="size-5 shrink-0" aria-hidden="true" />
            )}
            {expanded && <span className="font-heading text-label-lg font-medium">Collapse</span>}
          </button>
        </WithTooltip>
      </div>
    </aside>
  )
}
