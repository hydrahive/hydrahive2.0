import { useEffect, useMemo, useState } from "react"
import { Check, RefreshCw } from "lucide-react"
import { agentsApi } from "@/features/agents/api"
import { llmModelsApi } from "@/features/llm/api"
import type { AgentBrief } from "@/features/chat/types"
import { CockpitButton } from "../CockpitButton"

interface Props {
  agentId: string | null
  agents: AgentBrief[]
  onAgentChanged: (agent: AgentBrief) => void
}

export function ProjectAiSettingsPanel({ agentId, agents, onAgentChanged }: Props) {
  const agent = useMemo(() => agents.find((item) => item.id === agentId) ?? null, [agents, agentId])
  const [models, setModels] = useState<string[]>([])
  const [model, setModel] = useState("")
  const [depth, setDepth] = useState("normal")
  const [loadingModels, setLoadingModels] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setModel(agent?.llm_model ?? "")
    setMessage(null)
    setError(null)
  }, [agent?.id, agent?.llm_model])

  useEffect(() => {
    let alive = true
    setLoadingModels(true)
    llmModelsApi.byModality("chat")
      .then((result) => {
        if (!alive) return
        setModels(result.models.map((item) => item.id))
      })
      .catch(() => { if (alive) setModels([]) })
      .finally(() => { if (alive) setLoadingModels(false) })
    return () => { alive = false }
  }, [])

  const availableModels = useMemo(() => {
    const seen = new Set<string>()
    const next: string[] = []
    for (const item of [agent?.llm_model, ...models]) {
      if (!item || seen.has(item)) continue
      seen.add(item)
      next.push(item)
    }
    return next
  }, [agent?.llm_model, models])

  async function save() {
    if (!agent || !model.trim()) return
    setSaving(true)
    setMessage(null)
    setError(null)
    try {
      const updated = await agentsApi.update(agent.id, { llm_model: model.trim() })
      onAgentChanged({
        id: updated.id,
        name: updated.name,
        type: updated.type,
        llm_model: updated.llm_model,
        status: updated.status,
        is_buddy: false,
      })
      setModel(updated.llm_model)
      setMessage("Modell gespeichert. Neue Chat-Aufrufe nutzen dieses LLM.")
    } catch {
      setError("Modell konnte nicht gespeichert werden.")
    } finally {
      setSaving(false)
    }
  }

  const dirty = Boolean(agent && model.trim() && model.trim() !== agent.llm_model)

  return (
    <div className="space-y-3">
      {!agent ? (
        <p className="text-xs text-[#8d9ab0]">Kein Projekt-Agent ausgewählt.</p>
      ) : (
        <>
          <div>
            <label className="mb-1 block text-xs text-[#8d9ab0]">Modell</label>
            <select
              value={model}
              disabled={loadingModels || availableModels.length === 0}
              onChange={(event) => setModel(event.target.value)}
              className="w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm font-semibold text-[#e8eef8] outline-none hover:border-[#46617f] disabled:opacity-50"
            >
              {loadingModels ? <option value={model}>Lade Modelle…</option> : null}
              {!loadingModels && availableModels.length === 0 ? <option value="">Keine Modelle konfiguriert</option> : null}
              {availableModels.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            <p className="mt-1 text-[11px] text-[#8d9ab0]">
              Aktuell am Projekt-Agenten: <span className="font-mono text-[#69d7ff]">{agent.llm_model}</span>
            </p>
          </div>

          <div>
            <label className="mb-1 block text-xs text-[#8d9ab0]">Tiefe</label>
            <select
              value={depth}
              onChange={(event) => setDepth(event.target.value)}
              className="w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm font-semibold text-[#e8eef8] outline-none hover:border-[#46617f]"
            >
              <option value="fast">Schnell</option>
              <option value="normal">Normal</option>
              <option value="deep">Tief</option>
              <option value="max">Maximal</option>
            </select>
            <p className="mt-1 text-[11px] text-[#8d9ab0]">Tiefe ist vorbereitet; gespeichert wird aktuell das Modell.</p>
          </div>

          {error ? <p className="text-xs text-rose-300">{error}</p> : null}
          {message ? <p className="text-xs text-emerald-300">{message}</p> : null}

          <div className="flex gap-2">
            <CockpitButton tone="primary" disabled={!dirty || saving} onClick={() => void save()}>
              {saving ? <RefreshCw size={12} className="mr-1 inline animate-spin" /> : <Check size={12} className="mr-1 inline" />}
              Speichern
            </CockpitButton>
            <CockpitButton disabled={!dirty || saving} onClick={() => setModel(agent.llm_model)}>Zurücksetzen</CockpitButton>
          </div>
        </>
      )}
    </div>
  )
}
