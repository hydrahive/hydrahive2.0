import { useEffect, useState } from "react"
import { CockpitButton } from "../CockpitButton"
import { CockpitPanel } from "../CockpitPanel"
import { api } from "@/shared/api-client"

type TaskStatus = "open" | "in_progress" | "done" | "cancelled"
type TaskPriority = "low" | "medium" | "high"

interface Task {
  id: string
  project_id: string | null
  title: string
  status: TaskStatus
  priority: TaskPriority
}

const TASKS_BASE = "/modules/tasks/tasks"

const projectTasksApi = {
  list(projectId: string): Promise<Task[]> {
    return api.get<Task[]>(`${TASKS_BASE}?project_id=${encodeURIComponent(projectId)}`)
  },
  create(projectId: string, title: string, priority: TaskPriority): Promise<Task> {
    return api.post<Task>(TASKS_BASE, { project_id: projectId, title, priority })
  },
  updateStatus(taskId: string, status: TaskStatus): Promise<Task> {
    return api.patch<Task>(`${TASKS_BASE}/${taskId}`, { status })
  },
}

interface Props {
  projectId: string | null
}

export function ProjectTasksPanel({ projectId }: Props) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [title, setTitle] = useState("")
  const [priority, setPriority] = useState<TaskPriority>("medium")
  const [error, setError] = useState<string | null>(null)

  async function reload() {
    if (!projectId) {
      setTasks([])
      return
    }
    setLoading(true)
    setError(null)
    try {
      setTasks(await projectTasksApi.list(projectId))
    } catch {
      setTasks([])
      setError("Tasks konnten nicht geladen werden.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void reload() }, [projectId])

  async function createTask() {
    if (!projectId || !title.trim()) return
    setCreating(true)
    setError(null)
    try {
      const task = await projectTasksApi.create(projectId, title.trim(), priority)
      setTasks((cur) => [task, ...cur])
      setTitle("")
      setPriority("medium")
    } catch {
      setError("Task konnte nicht erstellt werden.")
    } finally {
      setCreating(false)
    }
  }

  async function setStatus(task: Task, status: TaskStatus) {
    setError(null)
    const before = tasks
    setTasks((cur) => cur.map((item) => item.id === task.id ? { ...item, status } : item))
    try {
      const updated = await projectTasksApi.updateStatus(task.id, status)
      setTasks((cur) => cur.map((item) => item.id === updated.id ? updated : item))
    } catch {
      setTasks(before)
      setError("Task-Status konnte nicht geändert werden.")
    }
  }

  return (
    <CockpitPanel title="Projekt-Tasks" eyebrow="Tasks" actions={<CockpitButton disabled={!projectId || loading} onClick={() => void reload()}>Refresh</CockpitButton>}>
      <div className="mb-3 space-y-2 rounded-[4px] border border-white/[8%] bg-black/20 p-2">
        <input
          value={title}
          disabled={!projectId || creating}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") void createTask() }}
          placeholder="Neuer Projekt-Task…"
          className="w-full rounded-[4px] border border-white/[10%] bg-zinc-950/70 px-2 py-1.5 text-sm text-zinc-100 outline-none placeholder:text-zinc-700 focus:border-cyan-400/30"
        />
        <div className="flex gap-2">
          <select
            value={priority}
            disabled={!projectId || creating}
            onChange={(e) => setPriority(e.target.value as TaskPriority)}
            className="min-w-0 flex-1 rounded-[4px] border border-white/[10%] bg-zinc-950/70 px-2 py-1.5 text-xs font-semibold text-zinc-300 outline-none"
          >
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
          </select>
          <CockpitButton tone="primary" disabled={!projectId || creating || !title.trim()} onClick={() => void createTask()}>Task +</CockpitButton>
        </div>
      </div>
      {error ? <p className="mb-2 text-xs text-rose-300">{error}</p> : null}
      {loading ? <p className="text-sm text-zinc-600">Lade Tasks…</p> : null}
      {!loading && tasks.length === 0 ? <p className="text-sm text-zinc-600">Keine Tasks für dieses Projekt.</p> : null}
      <div className="max-h-56 space-y-1.5 overflow-y-auto pr-1">
        {tasks.slice(0, 20).map((task) => (
          <div key={task.id} className="rounded-[4px] border border-white/[8%] bg-white/[3%] p-2">
            <div className="flex items-start justify-between gap-2">
              <p className="min-w-0 text-sm font-semibold text-zinc-200">{task.title}</p>
              <span className="shrink-0 rounded-[3px] bg-amber-400/15 px-1.5 py-0.5 text-[10px] font-black uppercase text-amber-200">
                {task.priority}
              </span>
            </div>
            <div className="mt-2 flex gap-1">
              {(["open", "in_progress", "done"] as TaskStatus[]).map((status) => (
                <button
                  key={status}
                  onClick={() => void setStatus(task, status)}
                  className={[
                    "rounded-[3px] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.08em]",
                    task.status === status ? "bg-cyan-400/15 text-cyan-100" : "bg-white/[5%] text-zinc-600 hover:text-zinc-300",
                  ].join(" ")}
                >
                  {status.replace("in_progress", "doing")}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </CockpitPanel>
  )
}
