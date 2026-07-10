import { useEffect, useState } from "react"
import { CockpitButton } from "../CockpitButton"
import { CockpitPanel } from "../CockpitPanel"
import { tasksApi } from "@/modules/tasks/api"
import type { Task } from "@/modules/tasks/types"

interface Props {
  projectId: string | null
}

export function ProjectTasksPanel({ projectId }: Props) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let alive = true
    if (!projectId) {
      setTasks([])
      return
    }
    setLoading(true)
    tasksApi.list({ project_id: projectId })
      .then((r) => { if (alive) setTasks(r) })
      .catch(() => { if (alive) setTasks([]) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [projectId])

  return (
    <CockpitPanel title="Projekt-Tasks" eyebrow="Tasks" actions={<CockpitButton disabled={!projectId}>Task +</CockpitButton>}>
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
            <p className="mt-0.5 text-[11px] text-zinc-600">{task.status}</p>
          </div>
        ))}
      </div>
    </CockpitPanel>
  )
}
