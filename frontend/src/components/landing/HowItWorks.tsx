const STEPS = [
  {
    title: "Bring your structure",
    body: "Describe it, upload CSVs, connect Postgres or pick a template.",
  },
  {
    title: "Review and add edge cases",
    body: "Check the schema graph, then choose the tricky cases to include.",
  },
  {
    title: "Generate, verify, export",
    body: "Every key and rule is checked. Download CSV, JSON or a ZIP.",
  },
]

export function HowItWorks() {
  return (
    <section
      id="how-it-works"
      aria-labelledby="how-it-works-title"
      className="w-full scroll-mt-16 bg-surface-low py-16 md:py-24"
    >
      <div className="mx-auto max-w-5xl px-margin md:px-margin-lg">
        <h2
          id="how-it-works-title"
          className="text-center font-heading text-headline-lg font-medium text-ink md:text-headline-xl"
        >
          From idea to test database in three steps
        </h2>
        <ol className="mt-12 grid grid-cols-1 gap-8 md:grid-cols-3">
          {STEPS.map((step, i) => (
            <li key={step.title} className="flex flex-col items-start rounded-xl bg-card p-6 shadow-sm">
              <span
                className="tabular flex size-9 items-center justify-center rounded-full bg-primary-tint font-heading text-label-md font-medium text-primary-deep"
                aria-hidden="true"
              >
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="mt-4 mb-2 font-heading text-headline-sm font-medium text-ink">{step.title}</h3>
              <p className="text-body-md text-ink-muted">{step.body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
