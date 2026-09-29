import { Button } from "@/components/ui/button"
import { HeroBackground } from "./HeroBackground"

interface HeroProps {
  onOpenStudio: () => void
  onTryExample: () => void
}

export function Hero({ onOpenStudio, onTryExample }: HeroProps) {
  return (
    <section
      aria-labelledby="hero-title"
      className="relative isolate w-full overflow-hidden pt-12 pb-16 md:pt-20 md:pb-24"
    >
      <HeroBackground />
      <div className="mx-auto flex max-w-[1440px] flex-col items-center px-margin text-center md:px-margin-lg">
        <h1
          id="hero-title"
          className="max-w-4xl font-heading text-display font-medium text-ink md:text-display-xl"
        >
          <span>Realistic test data,</span>
          <br />
          <span className="text-primary">ready in minutes.</span>
        </h1>
        <p className="mt-4 max-w-[560px] text-body-lg text-ink-muted md:mt-6">
          Describe your system, upload CSVs or connect Postgres. DatDub builds a connected dataset with
          real edge cases and checks every row.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
          <Button size="lg" onClick={onOpenStudio}>
            Open studio
          </Button>
          <Button size="lg" variant="secondary" onClick={onTryExample}>
            Try an example
          </Button>
        </div>
        <p className="mt-4 text-body-sm text-hint">No account needed. Nothing is stored.</p>
      </div>
    </section>
  )
}
