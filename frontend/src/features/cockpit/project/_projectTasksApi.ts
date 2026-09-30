import { api } from "@/shared/api-client"

export type TaskStatus = "open" | "in_progress" | "done" | "cancelled"
export type TaskPriority = "low" | "medium" | "high"

export interface Task {
  id: string
  project_id: string | null
  title: string
  description?: string | null
  status: TaskStatus
  priority: TaskPriority
  /** Anzahl früherer Fassungen (tasks-Modul ≥ 1.1.0), sonst undefined. */
  history_count?: number
}

export interface TaskVersion {
  title: string
  description: string
  changed_at: string
  source: "update" | "restored"
}

export const historyLabel = (count: number) => `Verlauf (${count})`
export const formatVersionTime = (iso: string) => iso.replace("T", " ").slice(0, 16)

const TASKS_BASE = "/modules/tasks/tasks"

export const projectTasksApi = {
  list(projectId: string): Promise<Task[]> {
    return api.get<Task[]>(`${TASKS_BASE}?project_id=${encodeURIComponent(projectId)}`)
  },
  create(projectId: string, title: string, priority: TaskPriority): Promise<Task> {
    return api.post<Task>(TASKS_BASE, { project_id: projectId, title, priority })
  },
  updateStatus(taskId: string, status: TaskStatus): Promise<Task> {
    return api.patch<Task>(`${TASKS_BASE}/${taskId}`, { status })
  },
  history(taskId: string): Promise<TaskVersion[]> {
    return api.get<TaskVersion[]>(`${TASKS_BASE}/${encodeURIComponent(taskId)}/history`)
  },
}
