import { Lock } from "lucide-react"
import { Card } from "@/components/shared/Card"
import { ErrorCallout } from "@/components/shared/ErrorCallout"
import { SubmitButton } from "@/components/shared/SubmitButton"
import { inputClass } from "@/lib/styles"
import { cn } from "@/lib/utils"
import { MIN_PROMPT_LENGTH, PROMPT_EXAMPLES } from "./promptExamples"
import { SourceLayout } from "./SourceLayout"
import { usePromptDraft } from "./usePromptDraft"

export function PromptSource() {
  const { prompt, setPrompt, loading, error, submit } = usePromptDraft()

  return (
    <SourceLayout
      title="Describe your system"
      subtitle="Explain what the system stores and how things relate. DatDub drafts the tables, keys and rules for you to review."
    >
      <Card>
        <label htmlFor="prompt" className="font-heading text-label-lg font-medium text-ink">
          What does your system do?
        </label>
        <textarea
          id="prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={loading}
          rows={8}
          aria-describedby="prompt-hint"
          placeholder="For example: a billing system with customers, invoices, invoice items and payments. An invoice total equals the sum of its items."
          className={cn(inputClass, "mt-2 min-h-44 resize-y py-3 leading-relaxed")}
        />

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-body-sm text-ink-muted">Examples:</span>
          {PROMPT_EXAMPLES.map((example) => (
            <button
              key={example.label}
              type="button"
              disabled={loading}
              onClick={() => setPrompt(example.text)}
              className="h-8 rounded-full border border-line bg-surface-low px-3 font-heading text-label-md font-medium text-ink-muted transition-colors hover:border-primary hover:text-primary-deep disabled:opacity-50"
            >
              {example.label}
            </button>
          ))}
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-line pt-5">
          <p id="prompt-hint" className="flex items-center gap-2 text-body-sm text-ink-muted">
            <Lock className="size-4 shrink-0" aria-hidden="true" />
            Only your text is sent to the AI. No files, no rows.
          </p>
          <SubmitButton
            loading={loading}
            loadingLabel="Drafting the schema…"
            disabled={prompt.trim().length < MIN_PROMPT_LENGTH}
            title={prompt.trim().length < MIN_PROMPT_LENGTH ? "Write at least a sentence first" : undefined}
            onClick={submit}
          >
            Draft schema
          </SubmitButton>
        </div>
      </Card>

      {error && <ErrorCallout className="mt-4" title="The schema could not be drafted" message={error} />}
    </SourceLayout>
  )
}
