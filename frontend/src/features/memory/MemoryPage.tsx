import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { BrainCircuit } from "lucide-react"
import { CollapsibleSidebar } from "@/shared/CollapsibleSidebar"
import { HelpButton } from "@/i18n/HelpButton"
import { agentsApi } from "@/features/agents/api"
import { AgentTabBar } from "@/features/agents/_AgentTabBar"
import type { Agent } from "@/features/agents/types"
import { MemoryTab } from "./MemoryTab"
import { CrystalsTab } from "./CrystalsTab"
import { SessionsTab } from "./SessionsTab"

type TabId = "memory" | "crystals" | "sessions"

export function MemoryPage() {
  const { t } = useTranslation("memory")
  const [agents, setAgents] = useState<Agent[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [tab, setTab] = useState<TabId>("memory")

  useEffect(() => {
    agentsApi.list().then((list) => {
      setAgents(list)
      if (list.length > 0) setActiveId(list[0].id)
    }).catch(() => {})
  }, [])

  const active = agents.find((a) => a.id === activeId) ?? null

  const TABS: { id: TabId; label: string }[] = [
    { id: "memory", label: t("tabs.memory") },
    { id: "crystals", label: t("tabs.crystals") },
    { id: "sessions", label: t("tabs.sessions") },
  ]

  return (
    <div className="flex h-[calc(100dvh-3rem)] -m-4 md:-m-6">
      {/* Main content */}
      <main className="flex-1 min-w-0 flex flex-col overflow-hidden">
        {/* Page header */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-white/[6%] flex-shrink-0">
          <BrainCircuit className="text-violet-400" size={20} />
          <div>
            <h1 className="text-lg font-semibold text-zinc-100">{t("title")}</h1>
            <p className="text-xs text-zinc-500 mt-0.5">
              {active ? active.name : t("no_agent_selected")}
            </p>
          </div>
          <HelpButton topic="memory" />
        </div>

        {active ? (
          <>
            <AgentTabBar tabs={TABS} active={tab} onChange={(id) => setTab(id as TabId)} />
            <div className="flex-1 overflow-y-auto">
              {tab === "memory" && <MemoryTab agentId={active.id} />}
              {tab === "crystals" && <CrystalsTab agentId={active.id} />}
              {tab === "sessions" && <SessionsTab agentId={active.id} />}
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center flex-1 text-sm text-zinc-600">
            {t("select_agent")}
          </div>
        )}
      </main>

      {/* Agent selector sidebar */}
      <CollapsibleSidebar>
        <div className="flex flex-col h-full">
          <div className="p-3 border-b border-white/[6%]">
            <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
              {t("sidebar.agents")}
            </p>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {agents.map((a) => (
              <button
                key={a.id}
                onClick={() => { setActiveId(a.id); setTab("memory") }}
                className={`w-full text-left px-3 py-2.5 rounded-lg transition-all text-sm ${
                  a.id === activeId
                    ? "bg-gradient-to-r from-indigo-600/20 to-violet-600/10 border-l-2 border-violet-500 text-white"
                    : "hover:bg-white/[3%] border-l-2 border-transparent text-zinc-300"
                }`}
              >
                <p className="truncate">{a.name}</p>
                <p className="text-[10px] text-zinc-600 mt-0.5 font-mono truncate">{a.id}</p>
              </button>
            ))}
          </div>
        </div>
      </CollapsibleSidebar>
    </div>
  )
}
