import { ArrowRight, type LucideIcon } from "lucide-react"

interface SourceCardProps {
  title: string
  description: string
  icon: LucideIcon
  badge?: string
  onSelect: () => void
}

export function SourceCard({ title, description, icon: Icon, badge, onSelect }: SourceCardProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className="group flex items-center justify-between rounded-xl border border-line bg-card p-7 text-left shadow-sm transition-[background-color,border-color,box-shadow] duration-200 hover:border-primary hover:bg-surface-low hover:shadow-md hover:shadow-primary-deep/5 hover:ring-1 hover:ring-primary"
    >
      <span className="flex items-start gap-4 pr-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-surface-low text-primary-deep transition-colors group-hover:bg-card">
          <Icon className="size-[22px]" aria-hidden="true" />
        </span>
        <span className="flex flex-col">
          <span className="flex items-center gap-2">
            <span className="font-heading text-headline-sm font-medium tracking-tight text-ink">{title}</span>
            {badge && (
              <span className="rounded-full bg-surface-high px-2 py-0.5 font-mono text-code-sm font-medium text-primary-deep">
                {badge}
              </span>
            )}
          </span>
          <span className="mt-1 text-body-md text-ink-muted">{description}</span>
        </span>
      </span>
      <span
        className="flex size-8 shrink-0 items-center justify-center rounded-full text-hint transition-[color,translate] group-hover:translate-x-1 group-hover:text-primary-deep"
        aria-hidden="true"
      >
        <ArrowRight className="size-5" />
      </span>
    </button>
  )
}
