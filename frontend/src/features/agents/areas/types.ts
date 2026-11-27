// Bereichs-Verzeichnis und -Status (docs/specs/agent-bereiche.md). Bereiche sind nur eine SICHT auf agent.tools (E1).
export type Mark = "risky" | "private" | "costly"

export interface Area {
  id: string
  group: string
  name: string
  sentence: string
  marks: Mark[]
  tools: string[]
  source: string
}

export interface AreaGroup { id: string; name: string }

/** GET /api/agent-areas?lang= */
export interface AreaCatalog { groups: AreaGroup[]; areas: Area[]; base: string[]; unassigned: string[]; categories?: Record<string, string[]> }

export type AreaStateName = "on" | "off" | "partial"

export interface AreaState {
  id: string
  state: AreaStateName
  have: string[]
  missing: string[]
  new: string[]
  via_category: string[]
}

/** GET /api/agents/{id}/areas */
export interface AreaStatus { areas: AreaState[]; editable: boolean }

export interface Suggestion { area: string; reason: string }
