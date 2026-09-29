import { ArrowLeft } from "lucide-react"
import { useStudio } from "@/state/useStudio"

/** Small "All sources" link at the top of every source sub-screen. */
export function SourceBackLink() {
  const { dispatch } = useStudio()
  return (
    <button
      type="button"
      onClick={() => dispatch({ type: "openSource", screen: "picker" })}
      className="inline-flex w-fit items-center gap-1 rounded-sm font-heading text-label-lg font-medium text-ink-muted transition-colors hover:text-primary-deep"
    >
      <ArrowLeft className="size-4" aria-hidden="true" />
      All sources
    </button>
  )
}
