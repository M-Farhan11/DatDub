import { useState, type ReactNode } from "react"
import { cn } from "@/lib/utils"
import type { StudioState } from "@/state/studioReducer"
import { useStudio } from "@/state/useStudio"
import { Sidebar, type Workspace, type WorkspaceState } from "./Sidebar"
import { TopBar } from "./TopBar"

interface AppShellProps {
  children: ReactNode
  onHome: () => void
}

/** Which sidebar workspace is active, and why the others may be unavailable. */
function workspaceState(state: StudioState): WorkspaceState {
  const hasInvoices = Boolean(state.schema?.document_hints?.invoice)
  const disabledReason: WorkspaceState["disabledReason"] = {}
  if (!state.schema) disabledReason.relational = "choose a source first"
  if (!state.result) {
    disabledReason.tabular = "generate a dataset first"
    disabledReason.documents = "generate a dataset first"
  }

  let active: Workspace | null = null
  if (state.step === "Schema") active = "relational"
  else if (state.step === "Results" && state.resultsTab === "data") active = "tabular"
  else if (state.step === "Results" && state.resultsTab === "invoices") active = "documents"

  // Documents only exist for invoice-like schemas; otherwise the item is hidden, not left dead.
  return { active, disabledReason, hidden: hasInvoices ? [] : ["documents"] }
}

export function AppShell({ children, onHome }: AppShellProps) {
  const { state, dispatch } = useStudio()
  const [expanded, setExpanded] = useState(false)
  const title = state.schema?.name ?? "New dataset"
  // The workspace sidebar only has something to offer once a schema exists.
  const showSidebar = state.step !== "Source"

  const openWorkspace = (workspace: Workspace) => {
    if (workspace === "relational") dispatch({ type: "goTo", step: "Schema" })
    else dispatch({ type: "openResults", tab: workspace === "tabular" ? "data" : "invoices" })
  }

  return (
    <div className="min-h-dvh bg-surface-low">
      {showSidebar && (
        <Sidebar
          expanded={expanded}
          onToggle={() => setExpanded((v) => !v)}
          onHome={onHome}
          workspace={workspaceState(state)}
          onOpen={openWorkspace}
        />
      )}
      <TopBar
        title={title}
        step={state.step}
        reached={state.reached}
        onSelectStep={(step) => dispatch({ type: "goTo", step })}
        sidebar={showSidebar ? (expanded ? "expanded" : "collapsed") : "none"}
        onHome={onHome}
      />
      {/* On small screens the expanded sidebar overlays the content instead of pushing it. */}
      <main
        className={cn(
          "flex min-h-dvh flex-col pt-16 transition-[padding] duration-200 ease-out",
          showSidebar && "pl-16",
          showSidebar && expanded && "md:pl-52",
        )}
      >
        {children}
      </main>
    </div>
  )
}
