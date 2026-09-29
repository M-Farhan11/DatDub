import { Lock, Maximize2, SquarePen } from "lucide-react"
import { ErrorCallout } from "@/components/shared/ErrorCallout"
import { SubmitButton } from "@/components/shared/SubmitButton"
import { inputClass } from "@/lib/styles"
import { cn } from "@/lib/utils"
import { PROMPT_EXAMPLES } from "./promptExamples"
import { usePromptDraft } from "./usePromptDraft"

interface QuickDescribeCardProps {
  /** Opens the full-size Describe screen. */
  onExpand: () => void
}

/** Featured source: type a description right on the picker and draft the schema in one step. */
export function QuickDescribeCard({ onExpand }: QuickDescribeCardProps) {
  const { prompt, setPrompt, loading, error, canSubmit, submit } = usePromptDraft()

  return (
    <section
      aria-labelledby="quick-describe-title"
      className="rounded-2xl border border-primary/25 bg-card p-6 shadow-md shadow-primary/5 ring-1 ring-primary/5 md:p-7"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:gap-4">
          <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
            <SquarePen className="size-5" aria-hidden="true" />
          </span>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 id="quick-describe-title" className="font-heading text-headline-md font-medium text-ink">
                Describe your system
              </h2>
              <span className="rounded-full bg-primary-tint px-2 py-0.5 font-heading text-label-md font-medium text-primary-deep">
                Fastest way to start
              </span>
            </div>
            <p className="mt-1 text-body-md text-ink-muted">
              Say what it stores and how things relate. DatDub drafts the tables, keys and rules for you to review.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onExpand}
          className="inline-flex items-center gap-1.5 rounded-full px-2 py-1 font-heading text-label-md font-medium text-ink-muted hover:bg-surface-low hover:text-ink"
        >
          <Maximize2 className="size-3.5" aria-hidden="true" />
          Full screen
        </button>
      </div>

      <label htmlFor="quick-prompt" className="sr-only">
        Describe your system
      </label>
      <textarea
        id="quick-prompt"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) void submit()
        }}
        disabled={loading}
        rows={3}
        aria-describedby="quick-prompt-hint"
        placeholder="For example: a clinic with patients, doctors and appointments. Each appointment has one patient and one doctor."
        className={cn(inputClass, "mt-5 min-h-24 resize-y py-3 leading-relaxed")}
      />

      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-body-sm text-ink-muted">Try:</span>
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
        <SubmitButton
          loading={loading}
          loadingLabel="Drafting the schema…"
          disabled={!canSubmit}
          title={!canSubmit && !loading ? "Write at least a sentence first" : undefined}
          onClick={submit}
        >
          Draft schema
        </SubmitButton>
      </div>

      <p id="quick-prompt-hint" className="mt-4 flex items-center gap-2 text-body-sm text-hint">
        <Lock className="size-3.5 shrink-0" aria-hidden="true" />
        Only your text is sent to the AI. No files, no rows. Press Ctrl + Enter to draft.
      </p>

      {error && <ErrorCallout className="mt-4" title="The schema could not be drafted" message={error} />}
    </section>
  )
}
