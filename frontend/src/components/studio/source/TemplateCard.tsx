import { ArrowRight, Loader2, Table } from "lucide-react"
import type { TemplateSummary } from "@/api/types"

interface TemplateCardProps {
  template: TemplateSummary
  loading: boolean
  disabled: boolean
  onSelect: () => void
}

export function TemplateCard({ template, loading, disabled, onSelect }: TemplateCardProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      disabled={disabled}
      aria-busy={loading}
      className="group flex flex-col items-start gap-3 rounded-xl border border-line bg-card p-6 text-left shadow-sm transition-[background-color,border-color,box-shadow] duration-200 hover:border-primary hover:bg-surface-low hover:shadow-md hover:ring-1 hover:ring-primary disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:border-line disabled:hover:bg-card disabled:hover:ring-0"
    >
      <span className="flex w-full items-center justify-between gap-3">
        <span className="font-heading text-headline-md font-medium tracking-tight text-ink">{template.name}</span>
        <span className="flex size-8 items-center justify-center rounded-full text-hint transition-[color,translate] group-hover:translate-x-1 group-hover:text-primary-deep">
          {loading ? (
            <Loader2 className="size-5 animate-spin" aria-hidden="true" />
          ) : (
            <ArrowRight className="size-5" aria-hidden="true" />
          )}
        </span>
      </span>
      <span className="text-body-md text-ink-muted">{template.description}</span>
      <span className="mt-auto inline-flex items-center gap-1.5 rounded-full bg-surface-high px-2.5 py-1 font-mono text-code-sm text-primary-deep">
        <Table className="size-3.5" aria-hidden="true" />
        {template.tables} tables
      </span>
      {loading && <span className="sr-only">Loading template</span>}
    </button>
  )
}
