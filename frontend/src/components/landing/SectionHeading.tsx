interface SectionHeadingProps {
  id: string
  title: string
  subtitle?: string
}

/** Centered section title + one-line subtitle used by every landing section. */
export function SectionHeading({ id, title, subtitle }: SectionHeadingProps) {
  return (
    <div className="mx-auto max-w-2xl text-center">
      <h2 id={id} className="font-heading text-headline-lg font-medium tracking-tight text-ink md:text-headline-xl">
        {title}
      </h2>
      {subtitle && <p className="mt-3 text-body-lg text-ink-muted">{subtitle}</p>}
    </div>
  )
}
