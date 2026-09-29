import { ArrowRight, Receipt } from "lucide-react"
import { SubmitButton } from "@/components/shared/SubmitButton"

interface ExampleBannerProps {
  loading: boolean
  onLoad: () => void
}

/** Quick start for first-time visitors: the finance template shows every step. */
export function ExampleBanner({ loading, onLoad }: ExampleBannerProps) {
  return (
    <section
      aria-labelledby="example-title"
      className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-dashed border-primary/30 bg-primary-tint/30 px-5 py-4"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-card text-primary-deep shadow-sm">
          <Receipt className="size-5" aria-hidden="true" />
        </span>
        <div>
          <h2 id="example-title" className="font-heading text-headline-sm font-medium text-ink">
            New here? Start with the finance example
          </h2>
          <p className="text-body-md text-ink-muted">
            Customers, invoices, line items and payments, ready to generate with invoice PDFs.
          </p>
        </div>
      </div>
      <SubmitButton variant="secondary" className="border border-line" loading={loading} loadingLabel="Loading…" onClick={onLoad}>
        Load finance example
        <ArrowRight aria-hidden="true" />
      </SubmitButton>
    </section>
  )
}
