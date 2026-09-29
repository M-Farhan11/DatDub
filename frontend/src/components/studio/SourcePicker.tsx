import { useEffect, useRef } from "react"
import { ArrowRight, Database, FileUp, LayoutTemplate, Loader2, SquarePen, type LucideIcon } from "lucide-react"
import { ErrorCallout } from "@/components/shared/ErrorCallout"
import type { SourceScreen } from "@/state/studioReducer"
import { useLoadTemplate } from "@/state/useLoadTemplate"
import { useStudio } from "@/state/useStudio"
import { SourceCard } from "./SourceCard"

interface SourceOption {
  screen: Exclude<SourceScreen, "picker">
  title: string
  description: string
  icon: LucideIcon
  badge?: string
}

const SOURCES: SourceOption[] = [
  {
    screen: "prompt",
    title: "Describe it",
    description: "Write what your system does and we draft the tables.",
    icon: SquarePen,
    badge: "Prompt",
  },
  {
    screen: "csv",
    title: "Upload CSV files",
    description: "One file per table. Types and keys are detected.",
    icon: FileUp,
  },
  {
    screen: "database",
    title: "Connect a database",
    description: "Postgres or Supabase, read-only. SQLite upload also works.",
    icon: Database,
  },
  {
    screen: "template",
    title: "Use a template",
    description: "Finance or e-commerce, ready to generate.",
    icon: LayoutTemplate,
  },
]

interface SourcePickerProps {
  /** Load the finance example straight away (from the landing page link). */
  autoLoadExample?: boolean
  onExampleStarted?: () => void
}

export function SourcePicker({ autoLoadExample = false, onExampleStarted }: SourcePickerProps) {
  const { dispatch } = useStudio()
  const { load, loadingId, error } = useLoadTemplate()
  const started = useRef(false)

  useEffect(() => {
    if (autoLoadExample && !started.current) {
      started.current = true
      onExampleStarted?.()
      void load("finance")
    }
  }, [autoLoadExample, load, onExampleStarted])

  const loadingExample = loadingId === "finance"

  return (
    <div className="mx-auto w-full max-w-[880px] px-gutter-lg pt-12 pb-24 md:pt-16">
      <div className="mb-10 text-center">
        <h1 className="font-heading text-headline-xl font-medium tracking-tight text-ink md:text-display">
          Where should we start?
        </h1>
        <p className="mx-auto mt-2 max-w-xl text-body-lg text-ink-muted">
          Pick a source. You review everything before any data is generated.
        </p>
      </div>

      {error && <ErrorCallout className="mb-6" title="The finance example could not be loaded" message={error} />}

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {SOURCES.map((source) => (
          <SourceCard
            key={source.screen}
            title={source.title}
            description={source.description}
            icon={source.icon}
            badge={source.badge}
            onSelect={() => dispatch({ type: "openSource", screen: source.screen })}
          />
        ))}
      </div>

      <div className="mt-12 flex flex-wrap items-center justify-center gap-2 text-body-md text-ink-muted">
        <span>Not sure where to begin?</span>
        <button
          type="button"
          onClick={() => void load("finance")}
          disabled={loadingExample}
          className="group inline-flex items-center gap-1 rounded-sm font-heading text-label-lg font-medium text-primary-deep hover:underline disabled:no-underline disabled:opacity-70"
        >
          {loadingExample ? "Loading the finance example…" : "Try the finance example"}
          {loadingExample ? (
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          ) : (
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
          )}
        </button>
      </div>
    </div>
  )
}
