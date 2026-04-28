import { useEffect, useState } from "react"
import { Folder, MessageCircle, X } from "lucide-react"
import { chatApi, type ProjectBrief } from "./api"
import type { AgentBrief } from "./types"

type Mode = "direct" | "project"

interface Props {
  onClose: () => void
  onCreate: (agentId: string, title: string, projectId?: string) => void
}

export function NewSessionDialog({ onClose, onCreate }: Props) {
  const [mode, setMode] = useState<Mode>("direct")
  const [agents, setAgents] = useState<AgentBrief[]>([])
  const [projects, setProjects] = useState<ProjectBrief[]>([])
  const [agentId, setAgentId] = useState("")
  const [projectId, setProjectId] = useState("")
  const [title, setTitle] = useState("")

  useEffect(() => {
    chatApi.listAgents().then((all) => {
      const active = all.filter((a) => a.status === "active" && a.type !== "project")
      setAgents(active)
      if (active.length > 0) setAgentId(active[0].id)
    }).catch(() => {})
    chatApi.listProjects().then((all) => {
      const active = all.filter((p) => p.status === "active")
      setProjects(active)
      if (active.length > 0) setProjectId(active[0].id)
    }).catch(() => {})
  }, [])

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (mode === "direct") {
      if (!agentId) return
      onCreate(agentId, title.trim() || "")
    } else {
      const p = projects.find((pr) => pr.id === projectId)
      if (!p) return
      onCreate(p.agent_id, title.trim() || "", p.id)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <form onSubmit={submit} onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-2xl border border-white/[8%] bg-zinc-900 p-6 shadow-2xl shadow-black/40 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">Neue Session</h2>
          <button type="button" onClick={onClose} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
            <X size={16} />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <ModeButton active={mode === "direct"} onClick={() => setMode("direct")} icon={MessageCircle}
            label="Direkter Chat" hint="Mit einem Master- oder Specialist-Agent" />
          <ModeButton active={mode === "project"} onClick={() => setMode("project")} icon={Folder}
            label="Im Projekt" hint="Mit einem Project-Agent in dessen Workspace" />
        </div>

        <div className="space-y-2">
          {mode === "direct" ? (
            <>
              <label className="block text-xs font-medium text-zinc-400">Agent</label>
              {agents.length === 0 ? (
                <p className="text-sm text-zinc-500 py-2">Kein aktiver Agent verfügbar.</p>
              ) : (
                <select value={agentId} onChange={(e) => setAgentId(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm">
                  {agents.map((a) => <option key={a.id} value={a.id} className="bg-zinc-950 text-zinc-200">{a.name} · {a.type} · {a.llm_model}</option>)}
                </select>
              )}
            </>
          ) : (
            <>
              <label className="block text-xs font-medium text-zinc-400">Projekt</label>
              {projects.length === 0 ? (
                <p className="text-sm text-zinc-500 py-2">Kein aktives Projekt vorhanden.</p>
              ) : (
                <select value={projectId} onChange={(e) => setProjectId(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm">
                  {projects.map((p) => <option key={p.id} value={p.id} className="bg-zinc-950 text-zinc-200">{p.name}</option>)}
                </select>
              )}
            </>
          )}
        </div>

        <div className="space-y-2">
          <label className="block text-xs font-medium text-zinc-400">Titel (optional)</label>
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)}
            placeholder="z.B. Recherche zur Idee XY"
            className="w-full px-3 py-2.5 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm placeholder:text-zinc-600" />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5">Abbrechen</button>
          <button type="submit"
            disabled={mode === "direct" ? !agentId : !projectId}
            className="px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-violet-900/20">
            Starten
          </button>
        </div>
      </form>
    </div>
  )
}

function ModeButton({ active, onClick, icon: Icon, label, hint }: {
  active: boolean; onClick: () => void; icon: typeof Folder; label: string; hint: string
}) {
  return (
    <button type="button" onClick={onClick}
      className={`flex flex-col items-start gap-1 p-3 rounded-lg border text-left transition-all ${
        active ? "border-violet-500/40 bg-violet-500/[8%]" : "border-white/[8%] bg-white/[2%] hover:bg-white/[4%]"
      }`}>
      <Icon size={14} className={active ? "text-violet-300" : "text-zinc-500"} />
      <p className={`text-sm font-medium ${active ? "text-zinc-100" : "text-zinc-400"}`}>{label}</p>
      <p className="text-[10.5px] text-zinc-500 leading-snug">{hint}</p>
    </button>
  )
}
