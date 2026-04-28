export interface Project {
  id: string
  name: string
  description: string
  members: string[]
  agent_id: string
  status: "active" | "archived"
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
