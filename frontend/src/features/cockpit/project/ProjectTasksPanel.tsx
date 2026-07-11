import { useEffect, useRef, useState } from "react"
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

type TaskFilter = "all" | "open" | "in_progress" | "done"

const FILTERS: { key: TaskFilter; label: string }[] = [
  { key: "all", label: "Alle" },
  { key: "open", label: "Offen" },
  { key: "in_progress", label: "Doing" },
  { key: "done", label: "Erledigt" },
]

// Offene Arbeit zuerst, Erledigtes/Abgebrochenes ans Ende.
const STATUS_ORDER: Record<TaskStatus, number> = { in_progress: 0, open: 1, done: 2, cancelled: 3 }

export function ProjectTasksPanel({ projectId }: Props) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [title, setTitle] = useState("")
  const [priority, setPriority] = useState<TaskPriority>("medium")
  const [filter, setFilter] = useState<TaskFilter>("all")
  const [error, setError] = useState<string | null>(null)
  const titleInputRef = useRef<HTMLInputElement>(null)

  const counts = tasks.reduce(
    (acc, task) => {
      acc.all += 1
      if (task.status === "open") acc.open += 1
      else if (task.status === "in_progress") acc.in_progress += 1
      else if (task.status === "done") acc.done += 1
      return acc
    },
    { all: 0, open: 0, in_progress: 0, done: 0 } as Record<TaskFilter, number>,
  )

  const visibleTasks = tasks
    .filter((task) => (filter === "all" ? true : task.status === filter))
    .slice()
    .sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status])

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
      setCreateOpen(false)
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

  function openCreate() {
    setCreateOpen(true)
    window.setTimeout(() => titleInputRef.current?.focus(), 0)
  }

  return (
    <CockpitPanel title="Projekt-Tasks" eyebrow="Tasks" actions={<CockpitButton disabled={!projectId || loading} onClick={openCreate}>Task +</CockpitButton>} className="flex min-h-0 flex-col">
      {createOpen && <div className="mb-3 space-y-2 rounded-[4px] border border-[#2a364b] bg-[#111827] p-2">
        <input
          ref={titleInputRef}
          value={title}
          disabled={!projectId || creating}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") void createTask() }}
          placeholder="Neuer Projekt-Task…"
          className="w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2 py-1.5 text-sm text-[#e8eef8] outline-none placeholder:text-[#8d9ab0] focus:border-[#46617f]"
        />
        <div className="flex gap-2">
          <select
            value={priority}
            disabled={!projectId || creating}
            onChange={(e) => setPriority(e.target.value as TaskPriority)}
            className="min-w-0 flex-1 rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2 py-1.5 text-xs font-semibold text-[#e8eef8] outline-none"
          >
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
          </select>
          <CockpitButton tone="primary" disabled={!projectId || creating || !title.trim()} onClick={() => void createTask()}>Task +</CockpitButton>
        </div>
      </div>}
      {projectId && tasks.length > 0 ? (
        <div className="mb-2 flex flex-wrap gap-1">
          {FILTERS.map((item) => (
            <button
              key={item.key}
              onClick={() => setFilter(item.key)}
              className={[
                "rounded-[3px] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.08em]",
                filter === item.key
                  ? "bg-cyan-400/15 text-cyan-100"
                  : "bg-white/[5%] text-zinc-500 hover:text-zinc-300",
              ].join(" ")}
            >
              {item.label} <span className="opacity-60">{counts[item.key]}</span>
            </button>
          ))}
        </div>
      ) : null}
      {error ? <p className="mb-2 text-xs text-rose-300">{error}</p> : null}
      {loading ? <p className="text-sm text-zinc-600">Lade Tasks…</p> : null}
      {!loading && tasks.length === 0 ? <p className="text-sm text-zinc-600">Keine Tasks für dieses Projekt.</p> : null}
      {!loading && tasks.length > 0 && visibleTasks.length === 0 ? <p className="text-sm text-zinc-600">Keine Tasks mit diesem Status.</p> : null}
      <div className="min-h-0 flex-1 space-y-1.5 overflow-y-auto pr-1">
        {visibleTasks.slice(0, 30).map((task) => (
          <div key={task.id} className="rounded-[4px] border border-[#223048] bg-[#111827] p-2">
            <div className="flex items-start justify-between gap-2">
              <p className="min-w-0 text-sm font-semibold text-[#e8eef8]">{task.title}</p>
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
