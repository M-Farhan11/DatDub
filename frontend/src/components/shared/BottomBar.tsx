import type { ReactNode } from "react"
import { ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"

interface BottomBarProps {
  onBack?: () => void
  backLabel?: string
  /** Short context in the middle, e.g. "5,000 customers, 3 edge cases". */
  summary?: ReactNode
  /** Primary action(s) on the right. */
  children?: ReactNode
}

/** Sticky action bar at the bottom of a step. */
export function BottomBar({ onBack, backLabel = "Back", summary, children }: BottomBarProps) {
  return (
    <div className="sticky bottom-0 z-30 mt-auto border-t border-line bg-card/95 backdrop-blur">
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
