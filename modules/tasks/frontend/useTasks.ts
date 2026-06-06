import { useCallback, useEffect, useState } from "react"
import { tasksApi } from "./api"
import type { Task, TaskStatus, TaskPriority } from "./types"

interface UseTasksOptions {
  status?: TaskStatus
  projectId?: string
  /** Poll interval in ms when panel is visible. Default: 5000 */
  pollMs?: number
}

export function useTasks(opts: UseTasksOptions = {}) {
  const { status, projectId, pollMs = 5000 } = opts
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await tasksApi.list({ status, project_id: projectId })
      setTasks(data)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ladefehler")
    } finally {
      setLoading(false)
    }
  }, [status, projectId])

  useEffect(() => {
    load()
    const timer = setInterval(load, pollMs)
    const onVisible = () => { if (!document.hidden) load() }
    document.addEventListener("visibilitychange", onVisible)
    return () => {
      clearInterval(timer)
      document.removeEventListener("visibilitychange", onVisible)
    }
  }, [load, pollMs])

  const complete = useCallback(async (taskId: string) => {
    await tasksApi.update(taskId, { status: "done" })
    setTasks((prev) => prev.map((t) => t.id === taskId ? { ...t, status: "done" } : t))
  }, [])

  const updateTask = useCallback(async (taskId: string, data: {
    title?: string
    description?: string
    status?: TaskStatus
    priority?: TaskPriority
  }) => {
    const updated = await tasksApi.update(taskId, data)
    setTasks((prev) => prev.map((t) => t.id === taskId ? updated : t))
    return updated
  }, [])

  const deleteTask = useCallback(async (taskId: string) => {
    await tasksApi.delete(taskId)
    setTasks((prev) => prev.filter((t) => t.id !== taskId))
  }, [])

  const createTask = useCallback(async (data: {
    title: string
    description?: string
    priority?: TaskPriority
    project_id?: string
  }) => {
    const created = await tasksApi.create(data)
    setTasks((prev) => [created, ...prev])
    return created
  }, [])

  return { tasks, loading, error, refresh: load, complete, updateTask, deleteTask, createTask }
}
