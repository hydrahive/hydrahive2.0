import { useEffect, useMemo, useState } from "react"
import { Check, RefreshCw, X } from "lucide-react"
import { agentsApi, mcpInfoApi, type McpServerBrief } from "@/features/agents/api"
import type { Agent, ToolMeta } from "@/features/agents/types"
import type { AgentBrief } from "@/features/chat/types"
import { llmModelsApi, type RegistryModel } from "@/features/llm/api"
import { CockpitButton } from "../CockpitButton"
import { ProjectAgentEditorTabs } from "./ProjectAgentEditorTabs"

interface Props {
  agentId: string
  onClose: () => void
  onSaved: (agent: AgentBrief) => void
}

export function ProjectAgentEditOverlay({ agentId, onClose, onSaved }: Props) {
  const [agent, setAgent] = useState<Agent | null>(null)
  const [draft, setDraft] = useState<Agent | null>(null)
  const [prompt, setPrompt] = useState("")
  const [savedPrompt, setSavedPrompt] = useState("")
  const [models, setModels] = useState<string[]>([])
  const [catalog, setCatalog] = useState<RegistryModel[]>([])
  const [tools, setTools] = useState<ToolMeta[]>([])
  const [mcpServers, setMcpServers] = useState<McpServerBrief[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    Promise.all([
      agentsApi.get(agentId),
      agentsApi.getSystemPrompt(agentId),
      llmModelsApi.byModality("chat").catch(() => ({ models: [], default: "" })),
      agentsApi.listTools().catch(() => []),
      mcpInfoApi.list().catch(() => []),
    ])
      .then(([agentData, promptData, modelData, toolData, mcpData]) => {
        if (!alive) return
        setAgent(agentData)
        setDraft(agentData)
        setPrompt(promptData.prompt ?? "")
        setSavedPrompt(promptData.prompt ?? "")
        setCatalog(modelData.models)
        setModels(modelData.models.map((item) => item.id))
        setTools(toolData)
        setMcpServers(mcpData)
      })
      .catch(() => { if (alive) setError("Agent konnte nicht geladen werden.") })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [agentId])

  const agentDirty = useMemo(
    () => Boolean(agent && draft && JSON.stringify(draft) !== JSON.stringify(agent)),
    [agent, draft],
  )
  const promptDirty = prompt !== savedPrompt
  const dirty = agentDirty || promptDirty

  function patch(fields: Partial<Agent>) {
    setDraft((current) => current ? { ...current, ...fields } : current)
    setMessage(null)
  }

  function discard() {
    setDraft(agent)
    setPrompt(savedPrompt)
    setError(null)
    setMessage(null)
  }

  async function save() {
    if (!agent || !draft || !draft.name.trim() || !draft.llm_model.trim()) return
    if (promptDirty && !prompt.trim()) {
      setError("Der Systemprompt darf nicht leer sein.")
      return
    }
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      let updated = agent
      if (agentDirty) {
        const {
          id: _id,
          type: _type,
          created_at: _createdAt,
          updated_at: _updatedAt,
          created_by: _createdBy,
          workspace: _workspace,
          project_id: _projectId,
          ...fields
        } = draft
        void _id; void _type; void _createdAt; void _updatedAt; void _createdBy
        void _workspace; void _projectId
        updated = await agentsApi.update(agent.id, fields)
      }
      if (promptDirty) await agentsApi.setSystemPrompt(agent.id, prompt)
      setAgent(updated)
      setDraft(updated)
      setSavedPrompt(prompt)
      onSaved(toBrief(updated))
      setMessage("Agent gespeichert.")
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Agent konnte nicht gespeichert werden.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="flex h-[90dvh] w-full max-w-6xl flex-col overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#0e1420] shadow-2xl">
        <header className="flex shrink-0 items-center gap-3 border-b border-[#2a364b] bg-[#131b2a] px-4 py-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#69d7ff]">{draft?.type === "specialist" ? "Projekt-Spezialist" : "Projekt-Agent"}</p>
            <h2 className="text-lg font-black text-[#e8eef8]">Vollständige Agenten-Einstellungen</h2>
          </div>
          <div className="flex-1" />
          <button onClick={onClose} className="rounded-[4px] p-2 text-[#8d9ab0] hover:bg-white/[6%] hover:text-[#e8eef8]" aria-label="Schließen">
            <X size={16} />
          </button>
        </header>

        {error ? <p className="mx-4 mt-3 rounded-[4px] border border-rose-400/25 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{error}</p> : null}
        {message ? <p className="mx-4 mt-3 rounded-[4px] border border-emerald-400/25 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">{message}</p> : null}
        {loading ? <p className="p-5 text-sm text-[#8d9ab0]">Lade Agent und Einstellungen…</p> : null}
        {agent && draft ? (
          <ProjectAgentEditorTabs
            agent={agent}
            draft={draft}
            prompt={prompt}
            models={models}
            catalog={catalog}
            tools={tools}
            mcpServers={mcpServers}
            onChange={patch}
            onPromptChange={(value) => { setPrompt(value); setMessage(null) }}
          />
        ) : null}

        <footer className="flex shrink-0 items-center gap-2 border-t border-[#2a364b] bg-[#0b111c] px-4 py-3">
          <p className="truncate text-xs text-[#8d9ab0]">Agent-ID: <span className="font-mono">{agentId}</span></p>
          <div className="flex-1" />
          {dirty ? <CockpitButton disabled={saving} onClick={discard}>Verwerfen</CockpitButton> : null}
          <CockpitButton disabled={saving} onClick={onClose}>Schließen</CockpitButton>
          <CockpitButton tone="primary" disabled={!dirty || saving || !draft?.name.trim() || !draft?.llm_model.trim() || (promptDirty && !prompt.trim())} onClick={() => void save()}>
            {saving ? <RefreshCw size={12} className="mr-1 inline animate-spin" /> : <Check size={12} className="mr-1 inline" />}
            Speichern
          </CockpitButton>
        </footer>
      </div>
    </div>
  )
}

function toBrief(agent: Agent): AgentBrief {
  return {
    id: agent.id,
    name: agent.name,
    type: agent.type,
    llm_model: agent.llm_model,
    status: agent.status,
    is_buddy: false,
  }
}
