import { Scale } from "lucide-react"
import type { Rule } from "@/api/types"
import { MonoText } from "@/components/shared/MonoText"
import { RULE_KIND_LABEL } from "./schemaText"

interface RulesPanelProps {
  rules: Rule[]
}

export function RulesPanel({ rules }: RulesPanelProps) {
  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-line px-5 py-4">
        <h2 className="font-heading text-headline-sm font-semibold text-ink">Business rules</h2>
        <p className="mt-0.5 text-body-sm text-ink-muted">
          Every generated row follows these. Select a column in the graph to see its details.
        </p>
      </header>
      {rules.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 px-6 py-10 text-center">
          <Scale className="size-6 text-hint" aria-hidden="true" />
          <p className="text-body-md text-ink-muted">
            No business rules were found. Keys, links and types are still enforced.
          </p>
        </div>
      ) : (
        <ul className="flex-1 divide-y divide-line overflow-y-auto">
          {rules.map((rule) => (
            <li key={rule.id} className="px-5 py-4">
              <div className="flex items-start justify-between gap-3">
                <p className="text-body-md text-ink">{rule.description}</p>
                <span className="shrink-0 rounded-full bg-surface-high px-2 py-0.5 font-heading text-label-md font-medium text-primary-deep">
                  {RULE_KIND_LABEL[rule.kind]}
                </span>
              </div>
              <MonoText className="mt-1 block text-code-sm text-hint">
                {rule.table}.{rule.column}
              </MonoText>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
