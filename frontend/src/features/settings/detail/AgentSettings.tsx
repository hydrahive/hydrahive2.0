import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { agentsApi } from "@/features/agents/api"
import { AgentForm } from "@/features/agents/AgentForm"
import { llmModelsApi, type RegistryModel } from "@/features/llm/api"
import type { Agent, ToolMeta } from "@/features/agents/types"

/**
 * Agenten-EINSTELLUNGEN für den Settings-Hub. Die Agentenliste rendert NICHT
 * hier, sondern im Submenü rechts (Tills Schema: Submenü = die Agenten). Diese
 * Komponente bekommt die gewählte agentId und zeigt nur dessen Settings-Form
 * (Overview/Modell/Tools/Mail/Skills/Soul) — ohne die alte Vollbild-Liste.
 */
export function AgentSettings({ itemId }: { itemId: string | null }) {
  const [agent, setAgent] = useState<Agent | null>(null)
  const [tools, setTools] = useState<ToolMeta[]>([])
  const [models, setModels] = useState<string[]>([])
  const [catalog, setCatalog] = useState<RegistryModel[]>([])
  const [loading, setLoading] = useState(false)

  // Stammdaten (Tools/Modelle) einmalig.
  useEffect(() => {
    agentsApi.listTools().then(setTools).catch(() => {})
    llmModelsApi.byModality("chat").then((res) => {
      setModels(res.models.map((m) => m.id))
      setCatalog(res.models)
    }).catch(() => {})
  }, [])

  // Gewählten Agenten laden.
  useEffect(() => {
    if (!itemId) { setAgent(null); return }
    setLoading(true)
    agentsApi.list()
      .then((list) => setAgent(list.find((a) => a.id === itemId) ?? null))
      .catch(() => setAgent(null))
      .finally(() => setLoading(false))
  }, [itemId])

  if (!itemId) {
    return (
      <p className="py-16 text-center text-sm text-zinc-500">
        Rechts einen Agenten wählen, um seine Einstellungen zu bearbeiten.
      </p>
    )
  }
  if (loading || !agent) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Loader2 size={20} className="animate-spin text-zinc-500" />
      </div>
    )
  }

  return (
    <AgentForm
      agent={agent}
      models={models}
      catalog={catalog}
      tools={tools}
      onSaved={setAgent}
      onDeleted={() => setAgent(null)}
    />
  )
}
