import { useState } from "react"
import { FolderPlus, X } from "lucide-react"
import type { AgentBrief } from "@/features/chat/types"
import { projectsApi } from "@/features/projects/api"
import type { Project } from "@/features/projects/types"
import { CockpitButton } from "../CockpitButton"

interface Props {
  agents: AgentBrief[]
  onClose: () => void
  onCreated: (project: Project) => void
}

export function ProjectCreateOverlay({ agents, onClose, onCreated }: Props) {
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [model, setModel] = useState(agents[0]?.llm_model ?? "")
  const [initGit, setInitGit] = useState(true)
  const [enableSamba, setEnableSamba] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function create() {
    if (!name.trim() || !model.trim() || saving) return
    setSaving(true)
    setError(null)
    try {
      const project = await projectsApi.create({
        name: name.trim(),
        description: description.trim(),
        members: [],
        llm_model: model,
        init_git: initGit,
      })
      if (enableSamba) await projectsApi.putSamba(project.id, true)
      onCreated(project)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Projekt konnte nicht angelegt werden.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[100] grid place-items-center bg-black/75 p-4 backdrop-blur-sm" role="presentation">
      <section role="dialog" aria-modal="true" aria-labelledby="project-create-title" className="w-full max-w-2xl overflow-hidden rounded-[6px] border border-[#3b4a63] bg-[#111827] shadow-2xl shadow-black/60">
        <header className="flex items-center justify-between gap-3 border-b border-[#2a364b] px-5 py-4">
          <div className="flex items-center gap-3"><FolderPlus size={20} className="text-[#69d7ff]" /><div><h2 id="project-create-title" className="font-black text-[#e8eef8]">Neues Projekt</h2><p className="text-xs text-[#8d9ab0]">Workspace, Projekt-Agent und optional Samba werden gemeinsam angelegt.</p></div></div>
          <button onClick={onClose} disabled={saving} aria-label="Schließen" className="rounded-[4px] border border-[#2a364b] p-2 text-[#8d9ab0] hover:text-[#e8eef8] disabled:opacity-40"><X size={16} /></button>
        </header>

        <div className="space-y-4 p-5">
          <label className="block text-xs font-bold uppercase tracking-[0.12em] text-[#69d7ff]">Projektname<input autoFocus value={name} onChange={(event) => setName(event.target.value)} maxLength={120} className="mt-2 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm font-normal normal-case tracking-normal text-[#e8eef8]" placeholder="z. B. Kunstprojekt" /></label>
          <label className="block text-xs font-bold uppercase tracking-[0.12em] text-[#69d7ff]">Beschreibung<textarea value={description} onChange={(event) => setDescription(event.target.value)} maxLength={2000} rows={4} className="mt-2 w-full resize-y rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm font-normal normal-case tracking-normal text-[#e8eef8]" placeholder="Wofür ist das Projekt gedacht?" /></label>
          <label className="block text-xs font-bold uppercase tracking-[0.12em] text-[#69d7ff]">Agent-Modell<select value={model} onChange={(event) => setModel(event.target.value)} className="mt-2 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm font-normal normal-case tracking-normal text-[#e8eef8]">{Array.from(new Set(agents.map((agent) => agent.llm_model).filter(Boolean))).map((item) => <option key={item}>{item}</option>)}</select></label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex items-start gap-3 rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-3 text-sm text-[#e8eef8]"><input type="checkbox" checked={initGit} onChange={(event) => setInitGit(event.target.checked)} className="mt-0.5" /><span><strong className="block">Git initialisieren</strong><span className="text-xs text-[#8d9ab0]">Lokales Repository im Workspace vorbereiten.</span></span></label>
            <label className="flex items-start gap-3 rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-3 text-sm text-[#e8eef8]"><input type="checkbox" checked={enableSamba} onChange={(event) => setEnableSamba(event.target.checked)} className="mt-0.5" /><span><strong className="block">Samba freigeben</strong><span className="text-xs text-[#8d9ab0]">Workspace direkt im Netzwerk sichtbar machen.</span></span></label>
          </div>
          {error && <div className="rounded-[4px] border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</div>}
        </div>

        <footer className="flex justify-end gap-2 border-t border-[#2a364b] px-5 py-4"><CockpitButton onClick={onClose} disabled={saving}>Abbrechen</CockpitButton><CockpitButton tone="primary" onClick={() => void create()} disabled={saving || !name.trim() || !model.trim()}>{saving ? "Wird angelegt…" : "Projekt anlegen"}</CockpitButton></footer>
      </section>
    </div>
  )
}
