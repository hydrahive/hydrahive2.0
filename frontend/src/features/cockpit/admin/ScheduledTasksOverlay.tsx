import { useCallback, useEffect, useState } from "react"
import { CheckCircle2, Pause, Play, RefreshCw, Trash2, X } from "lucide-react"
import { scheduledTasksApi, type ScheduledTask } from "@/features/scheduledTasks/api"
import { AdminFeedback, AdminStat } from "./ui"
import { AdminOverlay } from "./AdminOverlay"
import { CockpitButton } from "../CockpitButton"

export function ScheduledTasksOverlay({ onClose }: { onClose: () => void }) {
  const [tasks, setTasks] = useState<ScheduledTask[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try { setTasks(await scheduledTasksApi.adminList()); setError(null) }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Aufgaben konnten nicht geladen werden.") }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void refresh(); const timer = window.setInterval(() => void refresh(), 5000); return () => window.clearInterval(timer) }, [refresh])

  async function action(task: ScheduledTask, kind: "pause" | "resume" | "run" | "remove") {
    setBusy(task.task_id); setError(null)
    try {
      if (kind === "pause") await scheduledTasksApi.pause(task.task_id)
      if (kind === "resume") await scheduledTasksApi.resume(task.task_id)
      if (kind === "run") await scheduledTasksApi.run(task.task_id)
      if (kind === "remove") await scheduledTasksApi.remove(task.task_id)
      await refresh()
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Aktion fehlgeschlagen.") }
    finally { setBusy(null) }
  }

  return <AdminOverlay eyebrow="Admin · Automationen" title="Intervallaufgaben" onClose={onClose} maxWidthClass="max-w-6xl" headerActions={<CockpitButton onClick={() => void refresh()}><RefreshCw size={13} /></CockpitButton>}>
    <div className="space-y-6"><p className="text-sm text-[#8d9ab0]">Zentrale Verwaltung für direkte Agenten-/Buddy-Aufgaben und optionale Butler-Events.</p><div className="grid grid-cols-2 gap-3 sm:grid-cols-4"><AdminStat icon={CheckCircle2} label="Gesamt" value={tasks.length} /><AdminStat icon={Play} label="Aktiv" value={tasks.filter((task) => task.enabled).length} /><AdminStat icon={Pause} label="Laufend" value={tasks.filter((task) => task.running).length} /><AdminStat icon={X} label="Fehler" value={tasks.filter((task) => task.last_status === "failed").length} /></div>{error && <AdminFeedback tone="danger">{error}</AdminFeedback>}{loading ? <AdminFeedback loading>Lade Intervallaufgaben…</AdminFeedback> : tasks.length === 0 ? <AdminFeedback>Keine Intervallaufgaben angelegt.</AdminFeedback> : <div className="space-y-2">{tasks.map((task) => <div key={task.task_id} className="flex flex-wrap items-center gap-3 rounded-[4px] border border-[#2a364b] bg-[#111827] p-3"><div className="min-w-[240px] flex-1"><p className="text-sm font-bold text-[#e8eef8]">{task.title}</p><p className="mt-1 text-xs text-[#8d9ab0]">{task.target_type}:{task.target_id} · {task.owner} · alle {task.interval_seconds}s · {task.execution_mode}</p><p className="mt-1 text-[11px] text-[#5b6675]">Status: {task.last_status} · nächster Lauf: {task.next_run_at}</p>{task.last_error && <p className="mt-1 truncate text-xs text-rose-300">{task.last_error}</p>}</div><CockpitButton disabled={busy === task.task_id || task.running} onClick={() => void action(task, "run")}><Play size={12} /></CockpitButton>{task.enabled ? <CockpitButton disabled={busy === task.task_id} onClick={() => void action(task, "pause")}><Pause size={12} /></CockpitButton> : <CockpitButton disabled={busy === task.task_id} onClick={() => void action(task, "resume")}><RefreshCw size={12} /></CockpitButton>}<CockpitButton tone="danger" disabled={busy === task.task_id} onClick={() => void action(task, "remove")}><Trash2 size={12} /></CockpitButton></div>)}</div>}</div>
  </AdminOverlay>
}
