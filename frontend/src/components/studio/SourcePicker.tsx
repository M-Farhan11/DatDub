import { useEffect, useRef } from "react"
import { Database, FileSpreadsheet, LayoutTemplate, type LucideIcon } from "lucide-react"
import { ErrorCallout } from "@/components/shared/ErrorCallout"
import type { SourceScreen } from "@/state/studioReducer"
import { useLoadTemplate } from "@/state/useLoadTemplate"
import { useStudio } from "@/state/useStudio"
import { ExampleBanner } from "./source/ExampleBanner"
import { QuickDescribeCard } from "./source/QuickDescribeCard"
import { SourceOptionCard } from "./source/SourceOptionCard"

interface SourceOption {
  screen: Exclude<SourceScreen, "picker" | "prompt">
  title: string
  description: string
  icon: LucideIcon
  tags: string[]
}

const EXISTING_DATA: SourceOption[] = [
  {
    screen: "csv",
    title: "Upload CSV files",
    description: "One file per table. Types, keys and links are detected.",
    icon: FileSpreadsheet,
    tags: [".csv", "Multiple files"],
  },
  {
    screen: "database",
    title: "Connect a database",
    description: "Read the structure and a small sample, read-only.",
    icon: Database,
    tags: ["Postgres", "Supabase", "SQLite"],
  },
  {
    screen: "template",
    title: "Use a template",
    description: "A ready-made schema with keys and business rules.",
    icon: LayoutTemplate,
    tags: ["Finance", "E-commerce"],
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

  return (
    <div className="mx-auto w-full max-w-[960px] px-gutter-lg pt-10 pb-16 md:pt-12">
      <header className="mb-8 text-center">
        <h1 className="font-heading text-headline-xl font-medium tracking-tight text-ink md:text-display">
          Where should we start?
        </h1>
        <p className="mx-auto mt-2 max-w-xl text-body-lg text-ink-muted">
          Pick a source. You review everything before any data is generated.
        </p>
      </header>

      <QuickDescribeCard onExpand={() => dispatch({ type: "openSource", screen: "prompt" })} />

      <div className="mt-8">
        <h2 className="mb-3 font-heading text-label-lg font-medium text-ink-muted">Or start from existing data</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {EXISTING_DATA.map((option) => (
            <SourceOptionCard
              key={option.screen}
              title={option.title}
              description={option.description}
              icon={option.icon}
              tags={option.tags}
              onSelect={() => dispatch({ type: "openSource", screen: option.screen })}
            />
          ))}
        </div>
      </div>

      <div className="mt-8">
        {error && <ErrorCallout className="mb-4" title="The finance example could not be loaded" message={error} />}
        <ExampleBanner loading={loadingId === "finance"} onLoad={() => void load("finance")} />
      </div>
    </div>
  )
}
