import { useState } from "react"
import { Lock } from "lucide-react"
import { errorMessage, schemaFromPrompt } from "@/api/client"
import { Card } from "@/components/shared/Card"
import { ErrorCallout } from "@/components/shared/ErrorCallout"
import { SubmitButton } from "@/components/shared/SubmitButton"
import { inputClass } from "@/lib/styles"
import { cn } from "@/lib/utils"
import { useStudio } from "@/state/useStudio"
import { SourceLayout } from "./SourceLayout"

const EXAMPLES = [
  {
    label: "Online store",
    text: "An online store with customers, orders, order items and payments. Orders can have several items and one payment. Order totals equal the sum of their items.",
  },
  {
    label: "Clinic appointments",
    text: "A clinic with patients, doctors, appointments and invoices. Each appointment belongs to one patient and one doctor. Invoices are issued after the appointment date.",
  },
  {
    label: "SaaS subscriptions",
    text: "A SaaS product with accounts, users, subscriptions and monthly invoices. Each account has several users and one active subscription. Invoice amounts follow the subscription plan.",
  },
]

export function PromptSource() {
  const { dispatch } = useStudio()
  const [prompt, setPrompt] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await schemaFromPrompt(prompt.trim())
      dispatch({ type: "schemaLoaded", schema: res.schema, kind: "prompt", notes: res.notes })
    } catch (err) {
      setError(errorMessage(err))
      setLoading(false)
    }
  }

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
          {EXAMPLES.map((example) => (
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
            disabled={prompt.trim().length < 10}
            title={prompt.trim().length < 10 ? "Write at least a sentence first" : undefined}
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
