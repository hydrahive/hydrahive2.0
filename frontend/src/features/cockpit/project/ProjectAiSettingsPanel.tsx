import { useEffect, useMemo, useState } from "react"
import { Check, RefreshCw } from "lucide-react"
import { agentsApi } from "@/features/agents/api"
import { llmModelsApi } from "@/features/llm/api"
import { useEffortLevels } from "@/features/llm/effort"
import type { AgentBrief } from "@/features/chat/types"
import { CockpitButton } from "../CockpitButton"

interface Props { agentId: string | null; agents: AgentBrief[]; onAgentChanged: (agent: AgentBrief) => void }

export function ProjectAiSettingsPanel({ agentId, agents, onAgentChanged }: Props) {
  const agent = useMemo(() => agents.find((item) => item.id === agentId) ?? null, [agents, agentId])
  const [models, setModels] = useState<string[]>([])
  const [model, setModel] = useState("")
  const [depth, setDepth] = useState("")
  const [loadingModels, setLoadingModels] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const effortLevels = useEffortLevels(model)

  useEffect(() => {
    setModel(agent?.llm_model ?? "")
    setDepth(agent?.reasoning_effort ?? "")
    setMessage(null); setError(null)
  }, [agent?.id, agent?.llm_model, agent?.reasoning_effort])

  useEffect(() => {
    let alive = true; setLoadingModels(true)
    llmModelsApi.byModality("chat").then((result) => { if (alive) setModels(result.models.map((item) => item.id)) })
      .catch(() => { if (alive) setModels([]) }).finally(() => { if (alive) setLoadingModels(false) })
    return () => { alive = false }
  }, [])

  useEffect(() => {
    if (depth && effortLevels.length > 0 && !effortLevels.includes(depth)) setDepth("")
  }, [depth, effortLevels])

  const availableModels = useMemo(() => Array.from(new Set([agent?.llm_model, ...models].filter(Boolean) as string[])), [agent?.llm_model, models])
  const dirty = Boolean(agent && model.trim() && (model.trim() !== agent.llm_model || depth !== (agent.reasoning_effort ?? "")))

  async function save() {
    if (!agent || !model.trim()) return
    setSaving(true); setMessage(null); setError(null)
    try {
      const updated = await agentsApi.update(agent.id, { llm_model: model.trim(), reasoning_effort: depth })
      const next = { ...agent, llm_model: updated.llm_model, reasoning_effort: updated.reasoning_effort ?? "" }
      onAgentChanged(next); setModel(next.llm_model); setDepth(next.reasoning_effort ?? "")
      setMessage("Modell und Thinking-Tiefe gespeichert. Neue Aufrufe nutzen diese Vorgabe.")
    } catch { setError("KI-Einstellungen konnten nicht gespeichert werden.") }
    finally { setSaving(false) }
  }

  return <div className="space-y-3">
    {!agent ? <p className="text-xs text-[#8d9ab0]">Kein Projekt-Agent ausgewählt.</p> : <>
      <div><label className="mb-1 block text-xs text-[#8d9ab0]">Modell</label><select value={model} disabled={loadingModels || !availableModels.length} onChange={(event) => setModel(event.target.value)} className="w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm font-semibold text-[#e8eef8] outline-none hover:border-[#46617f] disabled:opacity-50">{loadingModels && <option value={model}>Lade Modelle…</option>}{availableModels.map((item) => <option key={item} value={item}>{item}</option>)}</select><p className="mt-1 text-[11px] text-[#8d9ab0]">Aktuell: <span className="font-mono text-[#69d7ff]">{agent.llm_model}</span></p></div>
      <div><label className="mb-1 block text-xs text-[#8d9ab0]">Thinking-Tiefe</label><select value={depth} disabled={!effortLevels.length} onChange={(event) => setDepth(event.target.value)} className="w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm font-semibold text-[#e8eef8] outline-none hover:border-[#46617f] disabled:opacity-50"><option value="">Modellstandard</option>{effortLevels.map((level) => <option key={level} value={level}>{effortLabel(level)}</option>)}</select><p className="mt-1 text-[11px] text-[#8d9ab0]">Standard für den Projekt-Agenten. Eine Session-Auswahl hat Vorrang.</p></div>
      {error && <p className="text-xs text-rose-300">{error}</p>}{message && <p className="text-xs text-emerald-300">{message}</p>}
      <div className="flex gap-2"><CockpitButton tone="primary" disabled={!dirty || saving} onClick={() => void save()}>{saving ? <RefreshCw size={12} className="mr-1 inline animate-spin" /> : <Check size={12} className="mr-1 inline" />}Speichern</CockpitButton><CockpitButton disabled={!dirty || saving} onClick={() => { setModel(agent.llm_model); setDepth(agent.reasoning_effort ?? "") }}>Zurücksetzen</CockpitButton></div>
    </>}
  </div>
}

function effortLabel(level: string) { return ({ low: "Low", medium: "Medium", high: "High", xhigh: "Extra High", max: "Max", ultra: "Ultra" } as Record<string, string>)[level] ?? level }
