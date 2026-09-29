import { Clock } from "lucide-react"
import { EmptyState } from "@/components/shared/EmptyState"
import { Button } from "@/components/ui/button"
import { useStudio } from "@/state/useStudio"

/** Shown when the backend answers 404 dataset_not_found (datasets expire after 60 minutes). */
export function ExpiredState() {
  const { dispatch } = useStudio()
  return (
    <div className="mx-auto w-full max-w-[880px] px-gutter-lg pt-16">
      <EmptyState
        icon={Clock}
        title="This dataset has expired. Generate it again."
        description="Datasets are kept for 60 minutes. Your schema and settings are still here, and the same seed gives the same data."
        action={<Button onClick={() => dispatch({ type: "clearResult" })}>Back to Configure</Button>}
      />
    </div>
  )
}
