import { ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ClosingCtaProps {
  onOpenStudio: () => void
  onTryExample: () => void
}

export function ClosingCta({ onOpenStudio, onTryExample }: ClosingCtaProps) {
  return (
    <section aria-labelledby="closing-title" className="w-full px-margin py-14 md:px-margin-lg md:py-16">
      <div className="dot-grid relative mx-auto flex max-w-[1100px] flex-col items-center overflow-hidden rounded-2xl border border-chrome bg-card px-6 py-12 text-center shadow-sm">
        <h2 id="closing-title" className="font-heading text-headline-lg font-medium tracking-tight text-ink md:text-headline-xl">
          Build your first test environment in minutes
        </h2>
        <p className="mt-3 max-w-xl text-body-lg text-ink-muted">
          Start with the finance example to see every step, then bring your own schema.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Button size="lg" onClick={onOpenStudio}>
            Open studio
            <ArrowRight aria-hidden="true" />
          </Button>
          <Button size="lg" variant="secondary" className="border border-chrome" onClick={onTryExample}>
            Try the finance example
          </Button>
        </div>
      </div>
    </section>
  )
}
