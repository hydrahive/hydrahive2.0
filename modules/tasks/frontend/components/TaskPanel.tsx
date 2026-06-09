import { useEffect, useState, type CSSProperties } from "react"
import { CheckSquare, ChevronDown, FolderOpen, Globe, Plus, Trash2 } from "lucide-react"
import { useTasks } from "../useTasks"
import type { Task, TaskStatus, TaskPriority } from "../types"

const STATUS_LABEL: Record<TaskStatus, string> = {
  open:        "Offen",
  in_progress: "In Arbeit",
  done:        "Erledigt",
  cancelled:   "Abgebrochen",
}

const STATUS_COLOR: Record<TaskStatus, string> = {
  open:        "text-zinc-400",
  in_progress: "text-amber-400",
  done:        "text-emerald-400",
  cancelled:   "text-zinc-600",
}

const PRIORITY_BADGE: Record<TaskPriority, string> = {
  high:   "text-rose-400 bg-rose-500/10",
  medium: "text-zinc-400 bg-zinc-500/10",
  low:    "text-zinc-600 bg-zinc-700/10",
}

const PRIORITY_LABEL: Record<TaskPriority, string> = {
  high: "!", medium: "~", low: "↓",
}

const FILTER_OPTIONS: Array<{ value: TaskStatus | "all"; label: string }> = [
  { value: "all",        label: "Alle" },
  { value: "open",       label: "Offen" },
  { value: "in_progress",label: "In Arbeit" },
  { value: "done",       label: "Erledigt" },
  { value: "cancelled",  label: "Abgebrochen" },
]

interface NewTaskFormProps {
  onSave: (title: string, priority: TaskPriority) => Promise<void>
  onCancel: () => void
}

function NewTaskForm({ onSave, onCancel }: NewTaskFormProps) {
  const [title, setTitle] = useState("")
  const [priority, setPriority] = useState<TaskPriority>("medium")
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    setSaving(true)
    try {
      await onSave(title.trim(), priority)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="p-2 border-b border-white/[6%] space-y-1.5">
      <input
        autoFocus
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Aufgabentitel…"
        className="w-full bg-zinc-800/60 border border-white/[8%] rounded px-2 py-1 text-xs text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50"
      />
      <div className="flex items-center gap-1.5">
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value as TaskPriority)}
          className="bg-zinc-800/60 border border-white/[8%] rounded px-1.5 py-1 text-[11px] text-zinc-400 focus:outline-none"
        >
          <option value="high">! Hoch</option>
          <option value="medium">~ Mittel</option>
          <option value="low">↓ Niedrig</option>
        </select>
        <div className="flex-1" />
        <button type="button" onClick={onCancel} className="text-[11px] text-zinc-600 hover:text-zinc-400 px-2 py-1">
          Abbrechen
        </button>
        <button
          type="submit"
          disabled={saving || !title.trim()}
          className="text-[11px] bg-violet-600/80 hover:bg-violet-500/80 disabled:opacity-40 text-white px-2.5 py-1 rounded transition-colors"
        >
          {saving ? "…" : "Hinzufügen"}
        </button>
      </div>
    </form>
  )
}

interface TaskRowProps {
  task: Task
  onStatusChange: (id: string, status: TaskStatus) => void
  onDelete: (id: string) => void
}

function TaskRow({ task, onStatusChange, onDelete }: TaskRowProps) {
  const isDone = task.status === "done" || task.status === "cancelled"

  return (
    <div className={`flex items-start gap-2 px-2 py-1.5 group hover:bg-white/[2%] rounded transition-colors ${isDone ? "opacity-50" : ""}`}>
      <button
        onClick={() => onStatusChange(task.id, isDone ? "open" : "done")}
        className={`flex-shrink-0 mt-0.5 w-3.5 h-3.5 rounded border transition-colors
          ${isDone
            ? "bg-emerald-500/20 border-emerald-500/40"
            : "border-white/[12%] hover:border-violet-500/50 hover:bg-violet-500/10"
          }`}
        title={isDone ? "Wieder öffnen" : "Als erledigt markieren"}
      >
        {isDone && <span className="flex items-center justify-center w-full h-full text-[8px] text-emerald-400">✓</span>}
      </button>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className={`inline-flex items-center px-1 rounded text-[9px] font-mono ${PRIORITY_BADGE[task.priority]}`}>
            {PRIORITY_LABEL[task.priority]}
          </span>
          <span className={`text-[11px] truncate ${isDone ? "line-through text-zinc-600" : "text-zinc-300"}`}>
            {task.title}
          </span>
        </div>
        {task.description && (
          <p className="text-[10px] text-zinc-600 mt-0.5 truncate ml-5">{task.description}</p>
        )}
      </div>

      <div className="flex items-center gap-1 flex-shrink-0">
        <div className="opacity-0 group-hover:opacity-100 transition-opacity">
          <select
            value={task.status}
            onChange={(e) => onStatusChange(task.id, e.target.value as TaskStatus)}
            onClick={(e) => e.stopPropagation()}
            className={`bg-transparent border-0 text-[10px] focus:outline-none cursor-pointer ${STATUS_COLOR[task.status]}`}
          >
            {(Object.entries(STATUS_LABEL) as [TaskStatus, string][]).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => onDelete(task.id)}
          className="text-zinc-700 hover:text-rose-400 transition-colors"
          title="Task löschen"
        >
          <Trash2 size={11} />
        </button>
      </div>
    </div>
  )
}

interface ProjectOption { id: string; name: string }

interface TaskPanelProps {
  projectId?: string | null
}

export function TaskPanel({ projectId: sessionProjectId }: TaskPanelProps = {}) {
  const [filter, setFilter] = useState<TaskStatus | "all">("all")
  const [showForm, setShowForm] = useState(false)
  // Wenn die Session kein Projekt hat, kann der User manuell eines wählen.
  const [manualProjectId, setManualProjectId] = useState<string | "">("")
  const [projects, setProjects] = useState<ProjectOption[]>([])

  const effectiveProjectId = sessionProjectId ?? (manualProjectId || undefined)

  useEffect(() => {
    if (sessionProjectId) return
    fetch("/api/projects", { credentials: "include" })
      .then((r) => r.ok ? r.json() : [])
      .then((list: ProjectOption[]) => setProjects(list))
      .catch(() => {})
  }, [sessionProjectId])

  const { tasks, loading, error, createTask, updateTask, deleteTask } = useTasks({
    status: filter === "all" ? undefined : filter,
    projectId: effectiveProjectId,
    pollMs: 5000,
  })

  async function handleCreate(title: string, priority: TaskPriority) {
    await createTask({ title, priority, project_id: effectiveProjectId })
    setShowForm(false)
  }

  async function handleStatusChange(id: string, status: TaskStatus) {
    await updateTask(id, { status })
  }

  return (
    <div className="flex flex-col h-full" style={{ "--c": "138,92,246" } as CSSProperties}>
      <div className="flex items-center gap-1.5 px-2.5 py-1.5 border-b border-white/[6%]">
        <CheckSquare size={12} className="text-violet-400 flex-shrink-0" />
        {sessionProjectId ? (
          <span className="flex items-center gap-0.5 text-[9px] text-violet-400/70 bg-violet-500/10 rounded px-1 py-0.5 flex-shrink-0">
            <FolderOpen size={9} /> Projekt
          </span>
        ) : projects.length > 0 ? (
          <div className="relative flex-shrink-0">
            <select
              value={manualProjectId}
              onChange={(e) => setManualProjectId(e.target.value)}
              className="appearance-none bg-zinc-800/60 border border-white/[8%] rounded pl-1.5 pr-5 py-0.5 text-[9px] text-zinc-400 focus:outline-none focus:border-violet-500/40 cursor-pointer"
            >
              <option value="">Alle Projekte</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <ChevronDown size={8} className="absolute right-1 top-1/2 -translate-y-1/2 text-zinc-600 pointer-events-none" />
          </div>
        ) : (
          <span className="flex items-center gap-0.5 text-[9px] text-zinc-500 flex-shrink-0">
            <Globe size={9} /> Alle
          </span>
        )}
        <div className="flex gap-0.5 flex-1 overflow-x-auto">
          {FILTER_OPTIONS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className={`px-2 py-0.5 rounded text-[10px] whitespace-nowrap transition-colors
                ${filter === value
                  ? "bg-violet-500/20 text-violet-300"
                  : "text-zinc-500 hover:text-zinc-300"
                }`}
            >
              {label}
            </button>
          ))}
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="flex-shrink-0 text-zinc-500 hover:text-violet-400 transition-colors"
          title="Neuen Task anlegen"
        >
          <Plus size={13} />
        </button>
      </div>

      {showForm && (
        <NewTaskForm
          onSave={handleCreate}
          onCancel={() => setShowForm(false)}
        />
      )}

      <div className="flex-1 min-h-0 overflow-y-auto py-1">
        {loading && tasks.length === 0 && (
          <p className="text-[11px] text-zinc-600 px-3 py-2">Laden…</p>
        )}
        {error && (
          <p className="text-[11px] text-rose-500 px-3 py-2">{error}</p>
        )}
        {!loading && tasks.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-2 py-8">
            <CheckSquare size={24} className="text-zinc-700" />
            <p className="text-[11px] text-zinc-600">Keine Aufgaben</p>
          </div>
        )}
        {tasks.map((task) => (
          <TaskRow
            key={task.id}
            task={task}
            onStatusChange={handleStatusChange}
            onDelete={deleteTask}
          />
        ))}
      </div>
    </div>
  )
}
