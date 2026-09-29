import type { ReactNode } from "react"
import { ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface BottomBarProps {
  onBack?: () => void
  backLabel?: string
  /** Short context in the middle, e.g. "5,000 customers, 3 edge cases". */
  summary?: ReactNode
  /** Primary action(s) on the right. */
  children?: ReactNode
  /** Sticky over scrolling content (default). Use false inside fixed-height layouts. */
  sticky?: boolean
}

/** Sticky action bar at the bottom of a step. */
export function BottomBar({ onBack, backLabel = "Back", summary, children, sticky = true }: BottomBarProps) {
  return (
    <div
      className={cn(
        "mt-auto shrink-0 border-t border-line bg-card",
        sticky && "sticky bottom-0 z-30 bg-card/95 backdrop-blur",
      )}
    >
      <div className="flex h-16 items-center gap-4 px-4 md:px-gutter-lg">
        {onBack ? (
          <Button variant="ghost" onClick={onBack}>
            <ArrowLeft aria-hidden="true" />
            {backLabel}
          </Button>
        ) : (
          <span />
        )}
        {summary && <div className="hidden min-w-0 flex-1 truncate text-body-md text-ink-muted md:block">{summary}</div>}
        <div className="ml-auto flex items-center gap-3">{children}</div>
      </div>
    </div>
  )
}
