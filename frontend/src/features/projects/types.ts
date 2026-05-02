export interface Project {
  id: string
  name: string
  description: string
  notes: string
  members: string[]
  agent_id: string
  status: "active" | "paused" | "archived"
  created_at: string
  updated_at: string
  created_by: string
  git_initialized: boolean
}

export interface ProjectCreate {
  name: string
  description: string
  members: string[]
  llm_model: string
  init_git: boolean
}

export interface ProjectSession {
  id: string
  agent_id: string
  user_id: string
  project_id: string
  title: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface ProjectGitStatus {
  initialized: boolean
  branch?: string
  remote_url?: string | null
  ahead?: number
  behind?: number
  commits?: { hash: string; subject: string; author: string; date: string }[]
}

export interface ProjectGitRepo {
  name: string
  status: ProjectGitStatus
  has_token: boolean
}

export type ServerKind = "vm" | "container"

export interface ProjectServer {
  kind: ServerKind
  id: string
  name: string
  owner: string
  desired_state: string
  actual_state: string
  cpu: number | null
  ram_mb: number | null
  network_mode: string
  project_id: string | null
  // VM-only
  disk_gb?: number
  // Container-only
  image?: string
}

export interface ProjectStats {
  total_sessions: number
  active_sessions: number
  total_messages: number
  total_tokens: number
  last_activity: string | null
}
