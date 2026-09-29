import { useState, type ReactNode } from "react"
import { cn } from "@/lib/utils"
import { useStudio } from "@/state/useStudio"
import { Sidebar } from "./Sidebar"
import { TopBar } from "./TopBar"

interface AppShellProps {
  children: ReactNode
  onHome: () => void
}

export function AppShell({ children, onHome }: AppShellProps) {
  const { state, dispatch } = useStudio()
  const [expanded, setExpanded] = useState(false)
  const title = state.schema?.name ?? "New dataset"

  return (
    <div className="min-h-dvh bg-surface-low">
      <Sidebar expanded={expanded} onToggle={() => setExpanded((v) => !v)} onHome={onHome} />
      <TopBar
        title={title}
        step={state.step}
        reached={state.reached}
        onSelectStep={(step) => dispatch({ type: "goTo", step })}
        sidebarExpanded={expanded}
      />
      {/* On small screens the expanded sidebar overlays the content instead of pushing it. */}
      <main
        className={cn(
          "flex min-h-dvh flex-col pt-16 pl-16 transition-[padding] duration-200 ease-out",
          expanded && "md:pl-52",
        )}
      >
        {children}
      </main>
    </div>
  )
}
