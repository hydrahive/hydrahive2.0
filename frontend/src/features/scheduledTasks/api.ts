import { api } from "@/shared/api-client"

export type ScheduledTask = {
  task_id: string
  owner: string
  scope: string
  project_id: string | null
  target_type: "agent" | "buddy"
  target_id: string
  title: string
  prompt: string
  execution_mode: "direct" | "butler_event"
  interval_seconds: number
  enabled: boolean
  running: boolean
  next_run_at: string
  last_run_at: string | null
  last_status: string
  last_error: string | null
  failure_count: number
}

export type ScheduledTaskInput = Pick<ScheduledTask, "title" | "prompt" | "target_type" | "target_id" | "execution_mode" | "interval_seconds"> & {
  project_id?: string | null
  enabled?: boolean
}

export const scheduledTasksApi = {
  list: (projectId?: string | null) => api.get<ScheduledTask[]>(projectId ? `/scheduled-tasks?project_id=${encodeURIComponent(projectId)}` : "/scheduled-tasks"),
  adminList: () => api.get<ScheduledTask[]>("/scheduled-tasks/admin/all"),
  create: (input: ScheduledTaskInput) => api.post<ScheduledTask>("/scheduled-tasks", input),
  pause: (id: string) => api.post<ScheduledTask>(`/scheduled-tasks/${id}/pause`, {}),
  resume: (id: string) => api.post<ScheduledTask>(`/scheduled-tasks/${id}/resume`, {}),
  run: (id: string) => api.post<{ queued: boolean }>(`/scheduled-tasks/${id}/run`, {}),
  remove: (id: string) => api.delete<void>(`/scheduled-tasks/${id}`),
}
