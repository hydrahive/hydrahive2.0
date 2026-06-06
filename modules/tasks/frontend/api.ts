import { api } from "@/shared/api-client"
import type { Task, TaskStatus, TaskPriority } from "./types"

const BASE = "/modules/tasks/tasks"

export const tasksApi = {
  list(params?: { status?: TaskStatus; project_id?: string }): Promise<Task[]> {
    const qs = new URLSearchParams()
    if (params?.status) qs.set("status", params.status)
    if (params?.project_id) qs.set("project_id", params.project_id)
    const q = qs.toString()
    return api.get<Task[]>(`${BASE}${q ? `?${q}` : ""}`)
  },

  create(data: {
    title: string
    description?: string
    priority?: TaskPriority
    project_id?: string
    session_id?: string
  }): Promise<Task> {
    return api.post<Task>(BASE, data)
  },

  update(taskId: string, data: {
    title?: string
    description?: string
    status?: TaskStatus
    priority?: TaskPriority
  }): Promise<Task> {
    return api.patch<Task>(`${BASE}/${taskId}`, data)
  },

  delete(taskId: string): Promise<void> {
    return api.delete(`${BASE}/${taskId}`)
  },
}
