import { MotionConfig } from "motion/react"
import { TooltipProvider } from "@/components/ui/tooltip"
import { StudioProvider } from "@/state/StudioContext"
import { Root } from "./Root"

export default function App() {
  return (
    // reducedMotion="user": transform animations are skipped when the OS asks for less motion.
    <MotionConfig reducedMotion="user">
      <TooltipProvider delayDuration={200}>
        <StudioProvider>
          <Root />
        </StudioProvider>
      </TooltipProvider>
    </MotionConfig>
  )
}
