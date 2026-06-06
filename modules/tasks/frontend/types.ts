export type TaskStatus = "open" | "in_progress" | "done" | "cancelled"
export type TaskPriority = "low" | "medium" | "high"

export interface Task {
  id: string
  username: string
  project_id: string | null
  session_id: string | null
  title: string
  description: string
  status: TaskStatus
  priority: TaskPriority
  created_at: string
  updated_at: string
}
