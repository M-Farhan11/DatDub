import { useEffect, useState } from "react"
import { errorMessage, getTemplates } from "@/api/client"
import type { TemplateSummary } from "@/api/types"
import { ErrorCallout } from "@/components/shared/ErrorCallout"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { Button } from "@/components/ui/button"
import { useLoadTemplate } from "@/state/useLoadTemplate"
import { SourceLayout } from "./SourceLayout"
import { TemplateCard } from "./TemplateCard"

export function TemplateSource() {
  const [templates, setTemplates] = useState<TemplateSummary[] | null>(null)
  const [listError, setListError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const { load, loadingId, error: loadError } = useLoadTemplate()

  useEffect(() => {
    let alive = true
    getTemplates()
      .then((list) => alive && setTemplates(list))
      .catch((err: unknown) => alive && setListError(errorMessage(err)))
    return () => {
      alive = false
    }
  }, [attempt])

  const retry = () => {
    setListError(null)
    setTemplates(null)
    setAttempt((n) => n + 1)
  }

  return (
    <SourceLayout
      title="Use a template"
      subtitle="Start from a ready-made schema with keys and business rules already in place."
    >
      {listError ? (
        <ErrorCallout
          title="Templates could not be loaded"
          message={listError}
          action={
            <Button size="sm" variant="secondary" className="border border-line" onClick={retry}>
              Try again
            </Button>
          }
        />
      ) : templates === null ? (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          {[0, 1].map((i) => (
            <div key={i} className="rounded-xl border border-line bg-card p-6">
              <LoadingSkeleton lines={3} lineClassName="h-4" label="Loading templates" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          {templates.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              loading={loadingId === template.id}
              disabled={loadingId !== null}
              onSelect={() => void load(template.id)}
            />
          ))}
        </div>
      )}

      {loadError && <ErrorCallout className="mt-4" title="The template could not be opened" message={loadError} />}
    </SourceLayout>
  )
}
