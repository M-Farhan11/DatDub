import { Check, Minus } from "lucide-react"
import { SectionHeading } from "./SectionHeading"

const ROWS = [
  "Every foreign key points to a real parent row",
  "Business rules hold: totals, date order, limits",
  "Edge cases added on purpose, with an answer key",
  "A validation report for every dataset",
  "Documents whose totals match the data",
  "The same seed gives the same dataset",
]

export function Comparison() {
  return (
    <section aria-labelledby="why-title" className="w-full border-y border-chrome/60 bg-panel py-14 md:py-16">
      <div className="mx-auto max-w-[900px] px-margin md:px-margin-lg">
        <SectionHeading
          id="why-title"
          title="Why not just fake data?"
          subtitle="Random generators fill columns one by one. Real applications need data that holds together."
        />
        <div className="mt-8 overflow-hidden rounded-xl border border-line bg-card shadow-sm">
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">DatDub compared with a random fake-data generator</caption>
            <thead className="bg-page/60">
              <tr className="font-heading text-label-lg text-ink-muted">
                <th scope="col" className="px-5 py-3.5 font-medium">What your tests need</th>
                <th scope="col" className="w-32 px-3 py-3.5 text-center font-medium sm:w-44">Random fake data</th>
                <th scope="col" className="w-28 px-3 py-3.5 text-center font-semibold text-primary-deep sm:w-36">DatDub</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {ROWS.map((row) => (
                <tr key={row}>
                  <th scope="row" className="px-5 py-3.5 text-body-md font-normal text-ink">{row}</th>
                  <td className="px-3 py-3.5 text-center">
                    <Minus className="mx-auto size-4 text-hint" aria-label="Usually not" />
                  </td>
                  <td className="px-3 py-3.5 text-center">
                    <span className="mx-auto flex size-6 items-center justify-center rounded-full bg-primary-tint">
                      <Check className="size-4 text-primary-deep" strokeWidth={2.5} aria-label="Yes" />
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
