import { useContext } from "react"
import { StudioContext, type StudioContextValue } from "./studioContextValue"

export function useStudio(): StudioContextValue {
  const ctx = useContext(StudioContext)
  if (!ctx) throw new Error("useStudio must be used inside <StudioProvider>")
  return ctx
}
