import { useEffect, useState } from "react"
import { LandingPage } from "@/components/landing/LandingPage"
import { AppShell } from "@/components/studio/AppShell"
import { StudioScreen } from "@/components/studio/StudioScreen"

type View = "landing" | "studio"

/** Switches between the landing page and the studio with plain React state. */
export function Root() {
  const [view, setView] = useState<View>("landing")

  // Each view starts at the top. Drop any landing anchor (#faq, #features…) so the
  // browser does not jump back to it, and skip smooth scrolling for this jump.
  useEffect(() => {
    if (window.location.hash) history.replaceState(null, "", window.location.pathname + window.location.search)
    window.scrollTo({ top: 0, left: 0, behavior: "instant" })
  }, [view])

  return view === "landing" ? (
    <LandingPage onLaunch={() => setView("studio")} />
  ) : (
    <AppShell onHome={() => setView("landing")}>
      <StudioScreen />
    </AppShell>
  )
}
