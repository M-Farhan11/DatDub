import { createContext, type Dispatch } from "react"
import type { ScenarioSelection } from "@/api/types"
import type { StudioAction, StudioState } from "./studioReducer"

export interface StudioContextValue {
  state: StudioState
  dispatch: Dispatch<StudioAction>
  /** Selected scenarios in the shape GenerateRequest.scenarios expects. */
  selections: ScenarioSelection[]
}

export const StudioContext = createContext<StudioContextValue | null>(null)
