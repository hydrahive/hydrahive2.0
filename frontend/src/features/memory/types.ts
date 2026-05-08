export interface MemoryEntry {
  key: string
  content: string
  confidence: number | null
  project: string | null
  expires_at: string | null
  created_at: string | null
  updated_at: string | null
  reinforcements: number
  is_latest: boolean
}

export interface MemoryResponse {
  agent_id: string
  total: number
  entries: MemoryEntry[]
}

export interface Crystal {
  id: string
  session_id: string
  project: string | null
  created_at: string | null
  narrative: string
  key_outcomes: string[]
  files_affected: string[]
  lessons: string[]
  observation_count: number
  source_observation_ids: string[]
}

export interface CrystalsResponse {
  agent_id: string
  total: number
  crystals: Crystal[]
}

export interface MemorySession {
  session_id: string
  project: string | null
  model: string | null
  status: string
  started_at: string | null
  ended_at: string | null
  first_prompt: string | null
  observation_count: number
  has_crystal: boolean
}

export interface MemorySessionsResponse {
  agent_id: string
  total: number
  sessions: MemorySession[]
}

export interface CompressedObservation {
  id: string
  type: string
  title: string
  facts: string[]
  concepts: string[]
  files: string[]
  importance: number
  narrative: string
  timestamp: string | null
}

export interface ObservationsResponse {
  agent_id: string
  session_id: string
  total: number
  observations: CompressedObservation[]
}
