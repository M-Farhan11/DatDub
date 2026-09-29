import { FlaskConical, Network, PackageCheck, Upload, type LucideIcon } from "lucide-react"
import { SectionHeading } from "./SectionHeading"

const STEPS: { icon: LucideIcon; title: string; body: string }[] = [
  {
    icon: Upload,
    title: "Bring your structure",
    body: "Describe your system, upload CSV files, connect Postgres or pick a template.",
  },
  {
    icon: Network,
    title: "Review the schema",
    body: "See every table and link on a graph. Correct types and personal-data flags.",
  },
  {
    icon: FlaskConical,
    title: "Add edge cases",
    body: "Pick the tricky records to include: overpayments, duplicates, missing values.",
  },
  {
    icon: PackageCheck,
    title: "Generate, check, export",
    body: "Get a validation report, invoice PDFs and your data as CSV, JSON or a ZIP.",
  },
]

export function HowItWorks() {
  return (
    <section id="how-it-works" aria-labelledby="how-it-works-title" className="w-full scroll-mt-16 py-14 md:py-16">
      <div className="mx-auto max-w-[1100px] px-margin md:px-margin-lg">
        <SectionHeading
          id="how-it-works-title"
          title="From idea to test database in four steps"
          subtitle="You review everything before a single row is generated."
        />
        <ol className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(({ icon: Icon, title, body }, i) => (
            <li key={title} className="relative flex flex-col rounded-xl border border-line bg-card p-6 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="flex size-10 items-center justify-center rounded-lg bg-primary-tint text-primary-deep">
                  <Icon className="size-5" aria-hidden="true" />
                </span>
                <span className="tabular font-mono text-code-md text-hint" aria-hidden="true">
                  {String(i + 1).padStart(2, "0")}
                </span>
              </div>
              <h3 className="mt-5 font-heading text-headline-sm font-medium text-ink">{title}</h3>
              <p className="mt-2 text-body-md text-ink-muted">{body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
