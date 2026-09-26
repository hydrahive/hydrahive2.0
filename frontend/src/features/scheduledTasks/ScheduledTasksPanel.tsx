import { useCallback, useEffect, useState } from "react"
import { Check, Pause, Play, Plus, RefreshCw, Trash2 } from "lucide-react"
import { scheduledTasksApi, type ScheduledTask, type ScheduledTaskInput } from "./api"

type Props = { targetType: "agent" | "buddy"; targetId: string; projectId?: string | null; heading?: string }

export function ScheduledTasksPanel({ targetType, targetId, projectId = null, heading = "Wiederkehrende Aufgaben" }: Props) {
  const [tasks, setTasks] = useState<ScheduledTask[]>([])
  const [showForm, setShowForm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [draft, setDraft] = useState({ title: "", prompt: "", interval: "60", mode: "direct" as "direct" | "butler_event" })

  const load = useCallback(async () => {
    try {
      const all = await scheduledTasksApi.list(projectId)
      setTasks(all.filter((task) => task.target_type === targetType && task.target_id === targetId))
      setError(null)
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Aufgaben konnten nicht geladen werden.") }
  }, [projectId, targetId, targetType])

  useEffect(() => { void load() }, [load])

  async function create() {
    if (!draft.title.trim() || !draft.prompt.trim()) return
    setBusy(true); setError(null)
    const input: ScheduledTaskInput = {
      title: draft.title.trim(), prompt: draft.prompt.trim(), target_type: targetType, target_id: targetId,
      project_id: projectId, execution_mode: draft.mode, interval_seconds: Math.max(10, Number(draft.interval) || 60),
    }
    try {
      await scheduledTasksApi.create(input)
      setDraft({ title: "", prompt: "", interval: "60", mode: "direct" }); setShowForm(false); await load()
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Aufgabe konnte nicht angelegt werden.") }
    finally { setBusy(false) }
  }

  async function action(task: ScheduledTask, kind: "pause" | "resume" | "run" | "remove") {
    setBusy(true); setError(null)
    try {
      if (kind === "pause") await scheduledTasksApi.pause(task.task_id)
      if (kind === "resume") await scheduledTasksApi.resume(task.task_id)
      if (kind === "run") await scheduledTasksApi.run(task.task_id)
      if (kind === "remove") await scheduledTasksApi.remove(task.task_id)
      await load()
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Aktion fehlgeschlagen.") }
    finally { setBusy(false) }
  }

  return <section className="space-y-3">
    <div className="flex items-center justify-between gap-3"><div><h3 className="text-sm font-bold text-[#e8eef8]">{heading}</h3><p className="mt-1 text-xs text-[#8d9ab0]">Direkt ausführen oder optional einen Butler-Flow auslösen.</p></div><button type="button" onClick={() => setShowForm((value) => !value)} className="inline-flex items-center gap-1 rounded-[4px] border border-[#69d7ff]/40 bg-[#163248] px-2.5 py-1.5 text-xs font-bold text-[#c8f2ff]"><Plus size={12} /> Aufgabe</button></div>
    {error && <p className="rounded-[4px] border border-rose-400/25 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">{error}</p>}
    {showForm && <div className="space-y-2 rounded-[4px] border border-[#2a364b] bg-[#111827] p-3">
      <input value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} placeholder="Titel" className="w-full rounded border border-[#2a364b] bg-[#0d1420] px-2.5 py-2 text-xs text-[#e8eef8]" />
      <textarea value={draft.prompt} onChange={(event) => setDraft({ ...draft, prompt: event.target.value })} placeholder="Was soll der Agent regelmäßig tun?" rows={3} className="w-full rounded border border-[#2a364b] bg-[#0d1420] px-2.5 py-2 text-xs text-[#e8eef8]" />
      <div className="grid grid-cols-2 gap-2"><label className="text-[11px] text-[#8d9ab0]">Intervall (Sekunden)<input type="number" min={10} value={draft.interval} onChange={(event) => setDraft({ ...draft, interval: event.target.value })} className="mt-1 w-full rounded border border-[#2a364b] bg-[#0d1420] px-2 py-1.5 text-xs text-[#e8eef8]" /></label><label className="text-[11px] text-[#8d9ab0]">Ausführung<select value={draft.mode} onChange={(event) => setDraft({ ...draft, mode: event.target.value as "direct" | "butler_event" })} className="mt-1 w-full rounded border border-[#2a364b] bg-[#0d1420] px-2 py-1.5 text-xs text-[#e8eef8]"><option value="direct">Direkt am Agenten</option><option value="butler_event">Butler-Event</option></select></label></div>
      <button type="button" disabled={busy || !draft.title.trim() || !draft.prompt.trim()} onClick={() => void create()} className="inline-flex items-center gap-1 rounded bg-[#1c6b45] px-3 py-1.5 text-xs font-bold text-white disabled:opacity-40"><Check size={12} /> Speichern</button>
    </div>}
    {tasks.length === 0 && !showForm && <p className="rounded-[4px] border border-dashed border-[#2a364b] px-3 py-4 text-xs text-[#5b6675]">Keine wiederkehrenden Aufgaben.</p>}
    {tasks.map((task) => <div key={task.task_id} className="flex items-center gap-3 rounded-[4px] border border-[#2a364b] bg-[#111827] px-3 py-2"><div className="min-w-0 flex-1"><p className="truncate text-xs font-bold text-[#e8eef8]">{task.title}</p><p className="mt-1 text-[11px] text-[#8d9ab0]">alle {task.interval_seconds}s · {task.execution_mode === "direct" ? "direkt" : "Butler"} · {task.last_status}</p>{task.last_error && <p className="truncate text-[10px] text-rose-300">{task.last_error}</p>}</div><button title="Jetzt ausführen" disabled={busy || task.running} onClick={() => void action(task, "run")} className="p-1 text-[#69d7ff] disabled:opacity-30"><Play size={13} /></button>{task.enabled ? <button title="Pausieren" disabled={busy} onClick={() => void action(task, "pause")} className="p-1 text-amber-300"><Pause size={13} /></button> : <button title="Fortsetzen" disabled={busy} onClick={() => void action(task, "resume")} className="p-1 text-emerald-300"><RefreshCw size={13} /></button>}<button title="Löschen" disabled={busy} onClick={() => void action(task, "remove")} className="p-1 text-rose-300"><Trash2 size={13} /></button></div>)}
  </section>
}
