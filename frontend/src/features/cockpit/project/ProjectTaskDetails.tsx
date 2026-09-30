import { useState } from "react"
import { History } from "lucide-react"
import { formatVersionTime, historyLabel, projectTasksApi, type TaskVersion } from "./_projectTasksApi"

/** Beschreibung + aufklappbarer Verlauf eines Projekt-Tasks (Task d61ae32b).
 *  Gleiche Daten wie „Verlauf (N)“ in der Werkstatt (tasks-Modul ≥ 1.1.0):
 *  `history_count` aus der Liste, Fassungen erst beim Aufklappen laden. */

export function ProjectTaskDetails({ taskId, description, historyCount }: {
  taskId: string
  description?: string | null
  historyCount?: number
}) {
  const [open, setOpen] = useState(false)
  const [versions, setVersions] = useState<TaskVersion[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const count = historyCount ?? 0
  const text = (description ?? "").trim()
  if (!text && count <= 0) return null

  async function toggle() {
    const next = !open
    setOpen(next)
    if (next && versions === null) {
      try {
        setVersions(await projectTasksApi.history(taskId))
      } catch (e) {
        setError(e instanceof Error ? e.message : "Verlauf nicht ladbar")
      }
    }
  }

  return (
    <div className="mt-1.5 space-y-1">
      {text && (
        <p title={text} className="line-clamp-2 whitespace-pre-wrap break-words text-xs text-zinc-400">{text}</p>
      )}
      {count > 0 && (
        <button onClick={() => void toggle()} className="inline-flex items-center gap-1 text-[10px] text-zinc-500 hover:text-zinc-300">
          <History size={10} /> {historyLabel(count)}
        </button>
      )}
      {open && (
        <div className="max-h-60 space-y-1.5 overflow-y-auto border-l border-white/[8%] pl-2">
          {error && <p className="text-[10px] text-rose-400">{error}</p>}
          {versions === null && !error && <p className="text-[10px] text-zinc-600">lädt…</p>}
          {versions?.length === 0 && <p className="text-[10px] text-zinc-600">Keine früheren Fassungen.</p>}
          {versions?.map((v, i) => (
            <div key={`${v.changed_at}-${i}`} className="text-[10px]">
              <div className="text-zinc-500">
                {formatVersionTime(v.changed_at)}
                {v.source === "restored" ? " · aus Chat-Verlauf wiederhergestellt" : ""}
              </div>
              {v.title && <div className="break-words text-zinc-400">{v.title}</div>}
              <p className="whitespace-pre-wrap break-words text-zinc-600">{v.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
