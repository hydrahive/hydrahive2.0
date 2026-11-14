import { useReducer } from "react"
import { fetchAgentTrace, type AgentTraceCall } from "./api"

export interface DrawerState {
  openSessionId: string | null
  calls: AgentTraceCall[]
}

type DrawerAction =
  | { type: "open"; sessionId: string }
  | { type: "loaded"; sessionId: string; calls: AgentTraceCall[] }
  | { type: "close" }

export const initialDrawerState: DrawerState = { openSessionId: null, calls: [] }

/** Reiner Reducer (Spec agent-office.md §4.2) — `loaded` für eine inzwischen verlassene Session wird
 *  ignoriert, damit eine verspätete Antwort nicht die Calls der aktuell geöffneten Session überschreibt. */
export function drawerReducer(state: DrawerState, action: DrawerAction): DrawerState {
  switch (action.type) {
    case "open":
      return { openSessionId: action.sessionId, calls: [] }
    case "loaded":
      return action.sessionId === state.openSessionId ? { ...state, calls: action.calls } : state
    case "close":
      return initialDrawerState
  }
}

/** Drawer-Zustand für den Live-Tool-Verlauf im Agenten-Büro. */
export function useTraceDrawer() {
  const [state, dispatch] = useReducer(drawerReducer, initialDrawerState)

  const open = async (sessionId: string) => {
    dispatch({ type: "open", sessionId })
    try {
      const trace = await fetchAgentTrace(sessionId)
      dispatch({ type: "loaded", sessionId, calls: trace.calls })
    } catch {
      // Drawer bleibt offen, nur leer — kein harter Fehler für eine Nebensächlichkeit.
    }
  }
  const close = () => dispatch({ type: "close" })

  return { openSessionId: state.openSessionId, calls: state.calls, open, close }
}
