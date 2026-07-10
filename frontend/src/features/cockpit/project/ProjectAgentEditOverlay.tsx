import { useEffect, useMemo, useState } from "react"
import { Check, RefreshCw, X } from "lucide-react"
import { agentsApi } from "@/features/agents/api"
import type { Agent } from "@/features/agents/types"
import type { AgentBrief } from "@/features/chat/types"
import { llmModelsApi } from "@/features/llm/api"
import { CockpitButton } from "../CockpitButton"

interface Props {
  agentId: string
  onClose: () => void
  onSaved: (agent: AgentBrief) => void
}

export function ProjectAgentEditOverlay({ agentId, onClose, onSaved }: Props) {
  const [agent, setAgent] = useState<Agent | null>(null)
  const [models, setModels] = useState<string[]>([])
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [model, setModel] = useState("")
  const [status, setStatus] = useState<"active" | "disabled">("active")
  const [systemPrompt, setSystemPrompt] = useState("")
  const [originalSystemPrompt, setOriginalSystemPrompt] = useState("")
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError(null)
    setMessage(null)
    Promise.all([
      agentsApi.get(agentId),
      agentsApi.getSystemPrompt(agentId),
      llmModelsApi.byModality("chat").catch(() => ({ models: [] })),
    ])
      .then(([agentData, promptData, modelData]) => {
        if (!alive) return
        setAgent(agentData)
        setName(agentData.name)
        setDescription(agentData.description ?? "")
        setModel(agentData.llm_model)
        setStatus(agentData.status)
        setSystemPrompt(promptData.prompt ?? "")
        setOriginalSystemPrompt(promptData.prompt ?? "")
        setModels(modelData.models.map((item) => item.id))
      })
      .catch(() => { if (alive) setError("Agent konnte nicht geladen werden.") })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [agentId])

  const availableModels = useMemo(() => {
    const seen = new Set<string>()
    const out: string[] = []
    for (const item of [agent?.llm_model, model, ...models]) {
      if (!item || seen.has(item)) continue
      seen.add(item)
      out.push(item)
    }
    return out
  }, [agent?.llm_model, model, models])

  const dirty = Boolean(agent && (
    name.trim() !== agent.name ||
    description !== (agent.description ?? "") ||
    model.trim() !== agent.llm_model ||
    status !== agent.status ||
    systemPrompt !== originalSystemPrompt
  ))

  async function save() {
    if (!agent || !name.trim() || !model.trim()) return
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      const updated = await agentsApi.update(agent.id, {
        name: name.trim(),
        description,
        llm_model: model.trim(),
        status,
      })
      await agentsApi.setSystemPrompt(agent.id, systemPrompt)
      setAgent(updated)
      setOriginalSystemPrompt(systemPrompt)
      onSaved({
        id: updated.id,
        name: updated.name,
        type: updated.type,
        llm_model: updated.llm_model,
        status: updated.status,
        is_buddy: false,
      })
      setMessage("Agent gespeichert.")
    } catch {
      setError("Agent konnte nicht gespeichert werden. Admin-Rechte erforderlich?")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="flex max-h-[86dvh] w-full max-w-3xl flex-col overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#0e1420] shadow-2xl">
        <header className="flex shrink-0 items-center gap-3 border-b border-[#2a364b] bg-[#131b2a] px-4 py-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#69d7ff]">Projekt-Agent</p>
            <h2 className="text-lg font-black text-[#e8eef8]">Agent bearbeiten</h2>
          </div>
          <div className="flex-1" />
          <button onClick={onClose} className="rounded-[4px] p-2 text-[#8d9ab0] hover:bg-white/[6%] hover:text-[#e8eef8]" aria-label="Schließen">
            <X size={16} />
          </button>
        </header>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
          {loading ? <p className="text-sm text-[#8d9ab0]">Lade Agent…</p> : null}
          {error ? <p className="rounded-[4px] border border-rose-400/25 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{error}</p> : null}
          {message ? <p className="rounded-[4px] border border-emerald-400/25 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">{message}</p> : null}

          {agent ? (
            <>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Name">
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    className="w-full rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 text-sm text-[#e8eef8] outline-none focus:border-[#69d7ff]/60"
                  />
                </Field>
                <Field label="Status">
                  <select
                    value={status}
                    onChange={(event) => setStatus(event.target.value as "active" | "disabled")}
                    className="w-full rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 text-sm text-[#e8eef8] outline-none focus:border-[#69d7ff]/60"
                  >
                    <option value="active">aktiv</option>
                    <option value="disabled">deaktiviert</option>
                  </select>
                </Field>
              </div>

              <Field label="Beschreibung">
                <textarea
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  rows={2}
                  className="w-full resize-none rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 text-sm text-[#e8eef8] outline-none focus:border-[#69d7ff]/60"
                />
              </Field>

              <Field label="Modell">
                <select
                  value={model}
                  onChange={(event) => setModel(event.target.value)}
                  className="w-full rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 text-sm text-[#e8eef8] outline-none focus:border-[#69d7ff]/60"
                >
                  {availableModels.map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </Field>

              <Field label="Systemprompt" hint="Wird direkt am Agenten gespeichert. Tools/Rechte bleiben aus Sicherheitsgründen in den Agent-Einstellungen.">
                <textarea
                  value={systemPrompt}
                  onChange={(event) => setSystemPrompt(event.target.value)}
                  rows={12}
                  className="w-full resize-y rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 font-mono text-xs leading-5 text-[#e8eef8] outline-none focus:border-[#69d7ff]/60"
                />
              </Field>
            </>
          ) : null}
        </div>

        <footer className="flex shrink-0 items-center gap-2 border-t border-[#2a364b] bg-[#0b111c] px-4 py-3">
          <p className="text-xs text-[#8d9ab0]">Agent-ID: <span className="font-mono">{agentId}</span></p>
          <div className="flex-1" />
          <CockpitButton disabled={saving} onClick={onClose}>Schließen</CockpitButton>
          <CockpitButton tone="primary" disabled={!dirty || saving || !agent || !name.trim() || !model.trim()} onClick={() => void save()}>
            {saving ? <RefreshCw size={12} className="mr-1 inline animate-spin" /> : <Check size={12} className="mr-1 inline" />}
            Speichern
          </CockpitButton>
        </footer>
      </div>
    </div>
  )
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-semibold text-[#8d9ab0]">{label}</label>
      {children}
      {hint ? <p className="mt-1 text-[11px] text-[#8d9ab0]">{hint}</p> : null}
    </div>
  )
}
