import { MousePointerClick, Scale } from "lucide-react"
import type { Rule } from "@/api/types"
import { describeRule } from "@/lib/ruleText"
import { RULE_KIND_LABEL } from "./schemaText"

interface RulesPanelProps {
  rules: Rule[]
}

export function RulesPanel({ rules }: RulesPanelProps) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="shrink-0 border-b border-line px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-heading text-headline-sm font-semibold text-ink">Business rules</h2>
          <span className="tabular rounded-full bg-surface-high px-2 py-0.5 font-mono text-code-sm text-primary-deep">
            {rules.length}
          </span>
        </div>
        <p className="mt-1 text-body-sm text-ink-muted">Every generated row follows these rules.</p>
      </header>

      {rules.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 px-6 py-10 text-center">
          <Scale className="size-6 text-hint" aria-hidden="true" />
          <p className="text-body-md text-ink-muted">
            No business rules were found. Keys, links and types are still enforced.
          </p>
        </div>
      ) : (
        <ul className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
          {rules.map((rule) => (
            <li key={rule.id} className="rounded-lg border border-line bg-surface-low/50 px-3.5 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-surface-high px-2 py-0.5 font-heading text-label-md font-medium text-primary-deep">
                  {RULE_KIND_LABEL[rule.kind]}
                </span>
                <span className="truncate font-mono text-code-sm text-hint">
                  {rule.table}.{rule.column}
                </span>
              </div>
              <p className="mt-1.5 text-body-md text-ink">{describeRule(rule)}</p>
            </li>
          ))}
        </ul>
      )}

      <p className="flex shrink-0 items-center gap-2 border-t border-line px-5 py-3 text-body-sm text-ink-muted">
        <MousePointerClick className="size-4 shrink-0" aria-hidden="true" />
        Click a column in the graph to see its details.
      </p>
    </div>
  )
}
