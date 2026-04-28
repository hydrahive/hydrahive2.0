import { useEffect, useState } from "react"
import { AgentForm } from "./AgentForm"
import { AgentList } from "./AgentList"
import { NewAgentDialog } from "./NewAgentDialog"
import { agentsApi, llmInfoApi } from "./api"
import type { Agent, ToolMeta } from "./types"

export function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [tools, setTools] = useState<ToolMeta[]>([])
  const [models, setModels] = useState<string[]>([])
  const [defaultModel, setDefaultModel] = useState("")
  const [showNew, setShowNew] = useState(false)

  async function loadAgents(selectId?: string) {
    const list = await agentsApi.list()
    setAgents(list)
    if (selectId) setActiveId(selectId)
    else if (!activeId && list.length > 0) setActiveId(list[0].id)
  }

  useEffect(() => {
    loadAgents().catch(() => {})
    agentsApi.listTools().then(setTools).catch(() => {})
    llmInfoApi.getModels().then((info) => {
      setModels(info.models)
      setDefaultModel(info.default_model)
    }).catch(() => {})
  }, [])

  function handleSaved(updated: Agent) {
    setAgents((cur) => cur.map((a) => (a.id === updated.id ? updated : a)))
  }

  function handleDeleted() {
    if (!activeId) return
    setAgents((cur) => cur.filter((a) => a.id !== activeId))
    setActiveId(null)
  }

  function handleCreated(id: string) {
    setShowNew(false)
    loadAgents(id)
  }

  const active = agents.find((a) => a.id === activeId) ?? null

  return (
    <div className="flex h-[calc(100vh-3.5rem)] -m-6">
      <main className="flex-1 min-w-0">
        {active ? (
          <AgentForm
            key={active.id}
            agent={active}
            models={models}
            tools={tools}
            onSaved={handleSaved}
            onDeleted={handleDeleted}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-sm text-zinc-600">
            Wähle links einen Agent oder lege einen neuen an.
          </div>
        )}
      </main>

      <aside className="w-72 border-l border-white/[6%] bg-white/[2%] flex-shrink-0">
        <AgentList
          agents={agents}
          activeId={activeId}
          onSelect={setActiveId}
          onNew={() => setShowNew(true)}
        />
      </aside>

      {showNew && (
        <NewAgentDialog
          models={models}
          defaultModel={defaultModel}
          onClose={() => setShowNew(false)}
          onCreated={handleCreated}
        />
      )}
    </div>
  )
}
