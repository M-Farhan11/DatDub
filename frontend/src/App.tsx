import { TooltipProvider } from "@/components/ui/tooltip"
import { StudioProvider } from "@/state/StudioContext"
import { Root } from "./Root"

export default function App() {
  return (
    <TooltipProvider delayDuration={200}>
      <StudioProvider>
        <Root />
      </StudioProvider>
    </TooltipProvider>
  )
}
