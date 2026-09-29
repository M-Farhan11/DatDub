import { lazy, Suspense } from "react"
import { LoadingSkeleton } from "@/components/shared/LoadingSkeleton"
import { useStudio } from "@/state/useStudio"
import { ConfigureStep } from "./configure/ConfigureStep"
import { ExportStep } from "./export/ExportStep"
import { SourcePicker } from "./SourcePicker"
import { CsvSource } from "./source/CsvSource"
import { DatabaseSource } from "./source/DatabaseSource"
import { PromptSource } from "./source/PromptSource"
import { TemplateSource } from "./source/TemplateSource"

// The graph library is only downloaded when the Schema step opens.
const SchemaStep = lazy(() => import("./schema/SchemaStep").then((m) => ({ default: m.SchemaStep })))
const ResultsStep = lazy(() => import("./results/ResultsStep").then((m) => ({ default: m.ResultsStep })))

function StepFallback() {
  return (
    <div className="px-4 pt-8 md:px-gutter-lg">
      <LoadingSkeleton lines={4} lineClassName="h-10" label="Loading step" />
    </div>
  )
}

interface StudioScreenProps {
  autoLoadExample: boolean
  onExampleStarted: () => void
}

/** Renders the screen for the current step. */
export function StudioScreen({ autoLoadExample, onExampleStarted }: StudioScreenProps) {
  const { state } = useStudio()

  if (state.step === "Source") {
    switch (state.sourceScreen) {
      case "prompt":
        return <PromptSource />
      case "csv":
        return <CsvSource />
      case "database":
        return <DatabaseSource />
      case "template":
        return <TemplateSource />
      default:
        return <SourcePicker autoLoadExample={autoLoadExample} onExampleStarted={onExampleStarted} />
    }
  }

  switch (state.step) {
    case "Schema":
      return (
        <Suspense fallback={<StepFallback />}>
          <SchemaStep />
        </Suspense>
      )
    case "Configure":
      return <ConfigureStep />
    case "Results":
      return (
        <Suspense fallback={<StepFallback />}>
          <ResultsStep />
        </Suspense>
      )
    case "Export":
      return <ExportStep />
  }
}
