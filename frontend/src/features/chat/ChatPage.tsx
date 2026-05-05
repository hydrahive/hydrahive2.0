import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { AssistantRuntimeProvider } from "@assistant-ui/react"
import { chatApi } from "./api"
import { agentsApi } from "@/features/agents/api"
import { useChatCompact } from "./useChatCompact"
import { MessageInput } from "./MessageInput"
import { NewSessionDialog } from "./NewSessionDialog"
import { SessionList } from "./SessionList"
import { ToolConfirmBanner } from "./ToolConfirmBanner"
import { CollapsibleSidebar } from "@/shared/CollapsibleSidebar"
import { ChatHeader } from "./_ChatHeader"
import { HydraThread } from "./_Thread"
import { useHydraRuntime } from "./_assistantRuntime"
import type { AgentBrief, Session } from "./types"
import type { ProjectBrief } from "./api"
import { useChat } from "./useChat"
import { isCommand, runCommand } from "@/features/buddy/commands"

export function ChatPage() {
  const { t } = useTranslation("chat")
  const [sessions, setSessions] = useState<Session[]>([])
  const [agents, setAgents] = useState<AgentBrief[]>([])
  const [projects, setProjects] = useState<ProjectBrief[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [showNew, setShowNew] = useState(false)
  const chat = useChat(activeId)
  const runtime = useHydraRuntime(chat.messages, chat.busy, chat.send, chat.cancel)

  const knownAgentIds = new Set(agents.map((a) => a.id))
  const buddyAgentIds = new Set(agents.filter((a) => a.is_buddy).map((a) => a.id))

  async function loadAll() {
    try {
      const [s, a, p] = await Promise.all([
        chatApi.listSessions(),
        chatApi.listAgents(),
        chatApi.listProjects(),
      ])
      setSessions(s); setAgents(a); setProjects(p)
      if (!activeId && s.length > 0) setActiveId(s[0].id)
    } catch { /* ignore */ }
  }

  useEffect(() => { loadAll() }, [])
  useEffect(() => { chat.reload() }, [activeId, chat.reload])

  async function handleNew(agentId: string, title: string, projectId?: string) {
    const s = await chatApi.createSession(agentId, title || undefined, projectId)
    setShowNew(false); setSessions((cur) => [s, ...cur]); setActiveId(s.id)
  }

  async function handleDelete(id: string) {
    await chatApi.deleteSession(id)
    setSessions((cur) => cur.filter((s) => s.id !== id))
    if (activeId === id) setActiveId(null)
  }

  const [tokenRefresh, setTokenRefresh] = useState(0)
  const { compacting, compactNote, handleCompact } = useChatCompact(
    activeId, chat.reload, () => setTokenRefresh((n) => n + 1),
  )

  const [cmdFeedback, setCmdFeedback] = useState<string | null>(null)

  async function handleSend(text: string, files: File[] = []) {
    if (isCommand(text)) {
      const result = await runCommand(text)
      setCmdFeedback(result.message)
      setTimeout(() => setCmdFeedback(null), 6000)
      return
    }
    await chat.send(text, files); loadAll(); setTokenRefresh((n) => n + 1)
  }

  const activeSession = sessions.find((s) => s.id === activeId) ?? null
  const activeOrphaned = activeSession ? !knownAgentIds.has(activeSession.agent_id) : false
  const activeAgent = activeSession ? (agents.find((a) => a.id === activeSession.agent_id) ?? null) : null

  const [systemPrompt, setSystemPrompt] = useState<string>("")
  useEffect(() => {
    setSystemPrompt("")
    if (!activeAgent) return
    let alive = true
    agentsApi.getSystemPrompt(activeAgent.id)
      .then((r) => { if (alive) setSystemPrompt(r.prompt) })
      .catch(() => {})
    return () => { alive = false }
  }, [activeAgent?.id])

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div className="flex h-[calc(100dvh-3rem)] -m-4 md:-m-6">
        <main className="flex-1 flex flex-col min-w-0">
          {activeSession ? (
            <>
              <ChatHeader
                session={activeSession} agent={activeAgent} orphaned={activeOrphaned}
                compacting={compacting} compactNote={compactNote}
                lastTurnTokens={chat.lastTurnTokens} busy={chat.busy}
                systemPrompt={systemPrompt} onCompact={handleCompact}
                onDelete={() => handleDelete(activeSession.id)} tokenRefresh={tokenRefresh}
                onSessionChanged={(updated) =>
                  setSessions((cur) => cur.map((s) => s.id === updated.id ? updated : s))
                }
              />
              <HydraThread />
              {chat.error && (
                <div className="px-4 py-2 text-xs text-rose-400 bg-rose-500/10 border-t border-rose-500/20">
                  {chat.error}
                </div>
              )}
              {chat.pendingConfirm && (
                <ToolConfirmBanner
                  pending={chat.pendingConfirm}
                  onApprove={() => chat.confirmTool("approve")}
                  onDeny={() => chat.confirmTool("deny")}
                />
              )}
              {cmdFeedback && (
                <div className="px-4 py-2 text-xs text-emerald-300 bg-emerald-500/10 border-t border-emerald-500/20 whitespace-pre-wrap">
                  {cmdFeedback}
                </div>
              )}
              <MessageInput onSend={handleSend} onCancel={chat.cancel} busy={chat.busy} disabled={activeOrphaned} />
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-sm text-zinc-600">
              {t("session.select_or_new")}
            </div>
          )}
        </main>

        <CollapsibleSidebar>
          <SessionList
            sessions={sessions} activeId={activeId}
            knownAgentIds={knownAgentIds} buddyAgentIds={buddyAgentIds} projects={projects}
            onSelect={setActiveId} onDelete={handleDelete} onNew={() => setShowNew(true)}
          />
        </CollapsibleSidebar>

        {showNew && <NewSessionDialog onClose={() => setShowNew(false)} onCreate={handleNew} />}
      </div>
    </AssistantRuntimeProvider>
  )
}
