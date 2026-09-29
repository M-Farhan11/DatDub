import { useEffect, useState } from "react"
import { LandingPage } from "@/components/landing/LandingPage"
import { AppShell } from "@/components/studio/AppShell"
import { StudioScreen } from "@/components/studio/StudioScreen"
import { useStudio } from "@/state/useStudio"

type View = "landing" | "studio"

/** Switches between the landing page and the studio with plain React state. */
export function Root() {
  const { dispatch } = useStudio()
  const [view, setView] = useState<View>("landing")
  // Set by "Try an example"; the source picker loads the finance template once, then clears it.
  const [pendingExample, setPendingExample] = useState(false)

  // Each view starts at the top of the page.
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [view])

  return view === "landing" ? (
    <LandingPage
      onOpenStudio={() => setView("studio")}
      onTryExample={() => {
        dispatch({ type: "openSource", screen: "picker" })
        setPendingExample(true)
        setView("studio")
      }}
    />
  ) : (
    <AppShell onHome={() => setView("landing")}>
      <StudioScreen autoLoadExample={pendingExample} onExampleStarted={() => setPendingExample(false)} />
    </AppShell>
  )
}
