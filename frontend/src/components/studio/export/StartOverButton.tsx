import { useState } from "react"
import { RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"

/** Two-step confirm so the current dataset is not cleared by accident. */
export function StartOverButton({ onConfirm }: { onConfirm: () => void }) {
  const [confirming, setConfirming] = useState(false)

  if (!confirming) {
    return (
      <Button variant="secondary" className="border border-line" onClick={() => setConfirming(true)}>
        <RotateCcw aria-hidden="true" />
        Start a new dataset
      </Button>
    )
  }

  return (
    <div role="group" aria-label="Confirm start over" className="flex flex-wrap items-center gap-3">
      <span className="text-body-md text-ink-muted">This clears the current schema and results.</span>
      <Button variant="ghost" size="sm" onClick={() => setConfirming(false)}>
        Cancel
      </Button>
      <Button size="sm" onClick={onConfirm} autoFocus>
        Start new
      </Button>
    </div>
  )
}
