import { useCallback, useEffect, useMemo, useState } from "react"
import { agentsApi } from "@/features/agents/api"
import { llmModelsApi } from "@/features/llm/api"
import { NewAgentDialog } from "@/features/agents/NewAgentDialog"
import type { Agent } from "@/features/agents/types"
import { ItemPicker } from "../ItemPicker"
import { AgentSettings } from "./AgentSettings"
import { agentItems } from "./itemsFrom"
import { useSelectedItem } from "./useSelectedItem"

/** Reiter „Agenten“: Auswahlfeld mit Suche oben, Einstellungen des gewählten Agenten darunter. */
export function AgentSection() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [models, setModels] = useState<string[]>([])
  const [creating, setCreating] = useState(false)

  const load = useCallback(() => {
    agentsApi.list().then(setAgents).catch(() => setAgents([])).finally(() => setLoading(false))
  }, [])
  useEffect(() => { load() }, [load])
  useEffect(() => {
    llmModelsApi.byModality("chat").then((res) => setModels(res.models.map((m) => m.id))).catch(() => {})
  }, [])

  const items = useMemo(() => agentItems(agents), [agents])
  const { value, select } = useSelectedItem(items, loading)

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 border-b border-[#2a364b] px-4 py-2.5">
        <ItemPicker label="Agent" items={items} value={value} onChange={select} onCreate={() => setCreating(true)} />
      </div>
      <div className="min-h-0 flex-1">
        <AgentSettings itemId={value} />
      </div>
      {creating && (
        <NewAgentDialog
          models={models}
          defaultModel={models[0] ?? ""}
          onClose={() => setCreating(false)}
          onCreated={(id) => { setCreating(false); load(); select(id) }}
        />
      )}
    </div>
  )
}
