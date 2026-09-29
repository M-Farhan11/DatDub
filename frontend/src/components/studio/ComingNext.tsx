import { ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ComingNextProps {
  name: string
  onBack: () => void
  backLabel?: string
}

/** Temporary placeholder for screens that are not built yet. */
export function ComingNext({ name, onBack, backLabel = "Back to sources" }: ComingNextProps) {
  return (
    <div className="mx-auto w-full max-w-[880px] px-gutter-lg pt-16 pb-24">
      <div className="flex flex-col items-center rounded-xl border border-dashed border-line bg-card px-6 py-16 text-center">
        <h1 className="font-heading text-headline-lg font-medium text-ink">Coming next: {name}</h1>
        <p className="mt-2 max-w-md text-body-md text-ink-muted">This screen is not built yet.</p>
        <Button variant="secondary" className="mt-6 border border-line" onClick={onBack}>
          <ArrowLeft aria-hidden="true" />
          {backLabel}
        </Button>
      </div>
    </div>
  )
}
