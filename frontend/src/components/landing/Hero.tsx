import { ArrowRight, Fingerprint, Repeat2, UserRoundCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { HeroBackground } from "./HeroBackground"

interface HeroProps {
  onOpenStudio: () => void
  onTryExample: () => void
}

const TRUST = [
  { icon: UserRoundCheck, text: "No account needed" },
  { icon: Fingerprint, text: "The AI never sees your rows" },
  { icon: Repeat2, text: "Same seed, same data" },
]

export function Hero({ onOpenStudio, onTryExample }: HeroProps) {
  return (
    <section
      aria-labelledby="hero-title"
      className="relative isolate w-full overflow-hidden pt-14 pb-12 md:pt-20 md:pb-16"
    >
      <HeroBackground />
      <div className="mx-auto flex max-w-[1200px] flex-col items-center px-margin text-center md:px-margin-lg">
        <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-chrome bg-card/80 px-3 py-1 font-heading text-label-md font-medium text-ink-muted shadow-sm">
          <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" />
          Synthetic test databases for developers and QA
        </p>
        <h1
          id="hero-title"
          className="max-w-none font-heading text-[40px] leading-[1.1] font-medium tracking-[-0.035em] text-balance text-ink sm:text-[50px] lg:text-[58px]"
        >
          Test environments, not just fake data.
        </h1>
        <p className="mt-6 max-w-[640px] text-body-lg text-ink-muted md:text-[18px] md:leading-[30px]">
          Describe your system, upload CSV files or connect Postgres. DatDub builds a complete, connected
          database with realistic edge cases, invoice documents and a validation report for every row.
        </p>
        <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
          <Button size="lg" onClick={onOpenStudio}>
            Open studio
            <ArrowRight aria-hidden="true" />
          </Button>
          <Button size="lg" variant="secondary" className="border border-chrome" onClick={onTryExample}>
            Try the finance example
          </Button>
        </div>
        <ul className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
          {TRUST.map(({ icon: Icon, text }) => (
            <li key={text} className="flex items-center gap-2 text-body-md text-ink-muted">
              <Icon className="size-4 text-primary" aria-hidden="true" />
              {text}
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
