import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Coins, Cpu, Download, FileText, GitMerge, Hammer, HelpCircle, Pencil, RotateCcw, Wand2 } from "lucide-react"
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
import { ChatBubbleThread } from "./_ChatBubbleThread"
import { useHydraRuntime } from "./_assistantRuntime"
import type { AgentBrief, Message, Session } from "./types"
import type { ProjectBrief } from "./api"
import { useChat } from "./useChat"
import { CmdPill } from "@/features/buddy/_BuddyCmdPill"
import { isCommand, runChatCommand } from "./commands"

export function ChatPage() {
  const { t } = useTranslation("chat")
  const [sessions, setSessions] = useState<Session[]>([])
  const [agents, setAgents] = useState<AgentBrief[]>([])
  const [projects, setProjects] = useState<ProjectBrief[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [showNew, setShowNew] = useState(false)
  const [localMsgs, setLocalMsgs] = useState<Message[]>([])
  const chat = useChat(activeId)
  const allMessages = [...chat.messages, ...localMsgs]
  const runtime = useHydraRuntime(allMessages, chat.busy, chat.send, chat.cancel)

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
  useEffect(() => { setLocalMsgs([]); chat.reload() }, [activeId, chat.reload])

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

  function appendLocal(role: "user" | "assistant", text: string) {
    setLocalMsgs((prev) => [
      ...prev,
      { id: `local-cmd-${Date.now()}-${prev.length}`, role,
        content: [{ type: "text", text }],
        created_at: new Date().toISOString(), token_count: null, metadata: {} },
    ])
  }

  async function handleSend(text: string, files: File[] = []) {
    if (!activeSession || !activeAgent) return
    if (isCommand(text)) {
      appendLocal("user", text)
      const result = await runChatCommand(text, activeSession, activeAgent, chat.messages)
      appendLocal("assistant", result.message)
      if (result.agentChanged) {
        setAgents((cur) => cur.map((a) => a.id === result.agentChanged!.id ? result.agentChanged! : a))
      }
      if (result.sessionChanged) {
        setSessions((cur) => cur.map((s) => s.id === result.sessionChanged!.id ? result.sessionChanged! : s))
      }
      if (result.newSessionId) {
        setLocalMsgs([])
        await loadAll()
        setActiveId(result.newSessionId)
        return
      }
      try {
        await chatApi.logCmd(activeSession.id, text, result.message)
        await chat.reload()
        setLocalMsgs([])
      } catch { /* localMsgs bleibt sichtbar */ }
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
        <main className="flex-1 flex flex-col min-w-0 p-3 md:p-4">
          {activeSession ? (
            <div
              className="relative flex flex-col rounded-[28px] border border-white/10 bg-gradient-to-b from-zinc-900/95 to-zinc-950/95 shadow-2xl shadow-[var(--hh-accent-soft)] overflow-hidden backdrop-blur w-full h-full"
            >
              <div className="absolute inset-0 pointer-events-none rounded-[28px] ring-1 ring-inset ring-white/[3%]" />
              <ChatHeader
                session={activeSession} agent={activeAgent} orphaned={activeOrphaned}
                compacting={compacting} compactNote={compactNote}
                lastTurnTokens={chat.lastTurnTokens} busy={chat.busy}
                systemPrompt={systemPrompt} onCompact={handleCompact}
                onDelete={() => handleDelete(activeSession.id)} tokenRefresh={tokenRefresh}
                onNewSession={async () => {
                  if (!activeAgent) return
                  const s = await chatApi.createSession(activeAgent.id)
                  setSessions((cur) => [s, ...cur]); setActiveId(s.id)
                }}
                onSessionChanged={(updated) =>
                  setSessions((cur) => cur.map((s) => s.id === updated.id ? updated : s))
                }
                onAgentChanged={(updated) =>
                  setAgents((cur) => cur.map((a) => a.id === updated.id ? updated : a))
                }
              />
              <ChatBubbleThread />
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
              <div className="border-t border-white/[6%] bg-black/30">
                <MessageInput
                  onSend={handleSend} onCancel={chat.cancel}
                  busy={chat.busy} disabled={activeOrphaned}
                  quickActions={(insert) => (
                    <>
                      <CmdPill icon={<HelpCircle size={11} />} label="help" color="sky" onClick={() => handleSend("/help")} />
                      <CmdPill icon={<RotateCcw size={11} />} label="clear" color="amber" onClick={() => handleSend("/clear")} />
                      <CmdPill icon={<Cpu size={11} />} label="model" color="violet" onClick={() => insert("/model")} />
                      <CmdPill icon={<GitMerge size={11} />} label="compact" color="emerald" onClick={() => handleSend("/compact")} />
                      <CmdPill icon={<Coins size={11} />} label="tokens" color="amber" onClick={() => handleSend("/tokens")} />
                      <CmdPill icon={<Pencil size={11} />} label="title" color="pink" onClick={() => insert("/title ")} />
                      <CmdPill icon={<Wand2 size={11} />} label="system" color="violet" onClick={() => handleSend("/system")} />
                      <CmdPill icon={<Hammer size={11} />} label="tools" color="sky" onClick={() => handleSend("/tools")} />
                      <CmdPill icon={<FileText size={11} />} label="agent" color="emerald" onClick={() => handleSend("/agent")} />
                      <CmdPill icon={<Download size={11} />} label="export" color="pink" onClick={() => handleSend("/export")} />
                    </>
                  )}
                />
              </div>
            </div>
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
