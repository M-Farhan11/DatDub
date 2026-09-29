import { FileCheck2, FlaskConical, Link2, Package, ScanSearch, ShieldCheck, type LucideIcon } from "lucide-react"
import { SectionHeading } from "./SectionHeading"

const FEATURES: { icon: LucideIcon; title: string; body: string }[] = [
  {
    icon: ScanSearch,
    title: "Understands your schema",
    body: "Finds types, keys, links and personal data, and shows how confident it is so you can correct it.",
  },
  {
    icon: Link2,
    title: "Keeps every relationship intact",
    body: "Child rows always point to real parents, and rules like invoice totals and date order are enforced while generating.",
  },
  {
    icon: FlaskConical,
    title: "Edge cases with an answer key",
    body: "Adds overpayments, duplicates or leap-day dates on purpose, and lists every changed record so your tests know what to expect.",
  },
  {
    icon: ShieldCheck,
    title: "Proof with every dataset",
    body: "Each run checks keys, links, types and business rules, and compares the data with your sample when you provide one.",
  },
  {
    icon: FileCheck2,
    title: "Documents that add up",
    body: "Invoice PDFs are rendered from the generated rows, so every total equals the sum of its line items.",
  },
  {
    icon: Package,
    title: "Export and reproduce",
    body: "Download CSV, JSON or one ZIP with the schema, report and answer key. The same seed gives the same data.",
  },
]

export function Features() {
  return (
    <section id="features" aria-labelledby="features-title" className="w-full scroll-mt-16 border-y border-chrome/60 bg-panel py-14 md:py-16">
      <div className="mx-auto max-w-[1100px] px-margin md:px-margin-lg">
        <SectionHeading
          id="features-title"
          title="Everything a realistic test database needs"
          subtitle="Built for developers, QA engineers and data teams who cannot use production data."
        />
        <ul className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, body }) => (
            <li key={title} className="rounded-xl border border-line bg-card p-6 shadow-sm">
              <span className="flex size-10 items-center justify-center rounded-lg bg-primary-tint text-primary-deep">
                <Icon className="size-5" aria-hidden="true" />
              </span>
              <h3 className="mt-5 font-heading text-headline-sm font-medium text-ink">{title}</h3>
              <p className="mt-2 text-body-md text-ink-muted">{body}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
