import { useMemo, useReducer, type ReactNode } from "react"
import type { ScenarioSelection } from "@/api/types"
import { StudioContext } from "./studioContextValue"
import { initialStudioState, studioReducer } from "./studioReducer"

/**
 * Holds the whole workflow in memory. Nothing here is written to
 * localStorage or sessionStorage, including database credentials.
 */
export function StudioProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(studioReducer, initialStudioState)

  const selections = useMemo<ScenarioSelection[]>(
    () =>
      state.proposals
        .filter((p) => p.id in state.selectedScenarios)
        .map((proposal) => ({ proposal, count: state.selectedScenarios[proposal.id] })),
    [state.proposals, state.selectedScenarios],
  )

  const value = useMemo(() => ({ state, dispatch, selections }), [state, selections])
  return <StudioContext.Provider value={value}>{children}</StudioContext.Provider>
}
