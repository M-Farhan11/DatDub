import { ArrowRight, type LucideIcon } from "lucide-react"

interface SourceOptionCardProps {
  title: string
  description: string
  icon: LucideIcon
  /** Short facts shown as tags, e.g. ".csv", "Multiple files". */
  tags: string[]
  onSelect: () => void
}

/** Compact, equal-height card for sources that start from existing data. */
export function SourceOptionCard({ title, description, icon: Icon, tags, onSelect }: SourceOptionCardProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className="group flex h-full flex-col rounded-xl border border-line bg-card p-5 text-left shadow-sm transition-[border-color,box-shadow,background-color] duration-200 hover:border-primary hover:bg-surface-low/40 hover:shadow-md hover:shadow-primary/5"
    >
      <span className="flex w-full items-center justify-between">
        <span className="flex size-10 items-center justify-center rounded-lg bg-primary-tint text-primary-deep">
          <Icon className="size-5" aria-hidden="true" />
        </span>
        <ArrowRight
          className="size-5 text-hint transition-[color,translate] group-hover:translate-x-1 group-hover:text-primary-deep"
          aria-hidden="true"
        />
      </span>
      <span className="mt-4 font-heading text-headline-sm font-medium text-ink">{title}</span>
      <span className="mt-1 text-body-md text-ink-muted">{description}</span>
      <span className="mt-auto flex flex-wrap gap-1.5 pt-4">
        {tags.map((tag) => (
          <span key={tag} className="rounded-md bg-surface-low px-2 py-0.5 font-mono text-code-sm text-ink-muted">
            {tag}
          </span>
        ))}
      </span>
    </button>
  )
}
