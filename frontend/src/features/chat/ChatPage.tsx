import { useEffect, useState } from "react"
import { AlertTriangle, Archive, Loader2 } from "lucide-react"
import { HelpButton } from "@/i18n/HelpButton"
import { chatApi, type ProjectBrief } from "./api"
import { MessageInput } from "./MessageInput"
import { MessageList } from "./MessageList"
import { NewSessionDialog } from "./NewSessionDialog"
import { SessionList } from "./SessionList"
import { TokenMeter } from "./TokenMeter"
import type { AgentBrief, Session } from "./types"
import { useChat } from "./useChat"

export function ChatPage() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [agents, setAgents] = useState<AgentBrief[]>([])
  const [projects, setProjects] = useState<ProjectBrief[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [showNew, setShowNew] = useState(false)
  const chat = useChat(activeId)

  const knownAgentIds = new Set(agents.map((a) => a.id))

  async function loadAll() {
    try {
      const [s, a, p] = await Promise.all([
        chatApi.listSessions(),
        chatApi.listAgents(),
        chatApi.listProjects(),
      ])
      setSessions(s)
      setAgents(a)
      setProjects(p)
      if (!activeId && s.length > 0) setActiveId(s[0].id)
    } catch {
      /* leer lassen */
    }
  }

  useEffect(() => {
    loadAll()
  }, [])

  useEffect(() => {
    chat.reload()
  }, [activeId, chat.reload])

  async function handleNew(agentId: string, title: string, projectId?: string) {
    const s = await chatApi.createSession(agentId, title || undefined, projectId)
    setShowNew(false)
    setSessions((cur) => [s, ...cur])
    setActiveId(s.id)
  }

  async function handleDelete(id: string) {
    await chatApi.deleteSession(id)
    setSessions((cur) => cur.filter((s) => s.id !== id))
    if (activeId === id) setActiveId(null)
  }

  const [tokenRefresh, setTokenRefresh] = useState(0)

  async function handleSend(text: string) {
    await chat.send(text)
    loadAll()
    setTokenRefresh((n) => n + 1)
  }

  const activeSession = sessions.find((s) => s.id === activeId) ?? null
  const activeOrphaned = activeSession ? !knownAgentIds.has(activeSession.agent_id) : false
  const activeAgent = activeSession ? agents.find((a) => a.id === activeSession.agent_id) : null
  const [compacting, setCompacting] = useState(false)
  const [compactNote, setCompactNote] = useState<string | null>(null)

  async function handleCompact() {
    if (!activeId) return
    setCompacting(true)
    setCompactNote(null)
    try {
      const r = await chatApi.compact(activeId)
      if (r.skipped) {
        setCompactNote(`Übersprungen: ${r.reason}`)
      } else {
        setCompactNote(
          `${r.summarized_count} Messages komprimiert, ${r.kept_count} behalten` +
          (r.tokens_before ? ` · ${r.tokens_before.toLocaleString("de")} Tokens` : ""),
        )
      }
      await chat.reload()
      setTokenRefresh((n) => n + 1)
    } catch (e) {
      setCompactNote(e instanceof Error ? e.message : "Fehler")
    } finally {
      setCompacting(false)
      setTimeout(() => setCompactNote(null), 5000)
    }
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] -m-6">
      <main className="flex-1 flex flex-col min-w-0">
        {activeSession ? (
          <>
            <div className="px-6 py-3 border-b border-white/[6%] flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <h2 className="text-sm font-medium text-zinc-200 truncate flex items-center gap-2">
                  {activeOrphaned && <AlertTriangle size={14} className="text-amber-400" />}
                  {activeSession.title}
                </h2>
                <p className="text-xs text-zinc-600 mt-0.5 flex items-center gap-2 flex-wrap">
                  <span>Session-ID: {activeSession.id.slice(0, 8)}…</span>
                  {activeAgent && (
                    <span className="text-zinc-500">
                      · <span className="text-violet-300/80 font-mono">{activeAgent.llm_model}</span>
                    </span>
                  )}
                  {chat.lastTurnTokens && !chat.busy && (
                    <span className="text-zinc-500" title="Input ↑ · Output ↓ · Cache-Read ⚡ · Cache-Write 💾">
                      · letzter Turn: <span className="tabular-nums">
                        <span className="text-emerald-400/80">↑{chat.lastTurnTokens.input.toLocaleString("de")}</span>
                        {" "}<span className="text-emerald-400/80">↓{chat.lastTurnTokens.output.toLocaleString("de")}</span>
                        {chat.lastTurnTokens.cache_read > 0 && (
                          <> {" "}<span className="text-cyan-400/80">⚡{chat.lastTurnTokens.cache_read.toLocaleString("de")}</span></>
                        )}
                        {chat.lastTurnTokens.cache_creation > 0 && (
                          <> {" "}<span className="text-amber-400/80">💾{chat.lastTurnTokens.cache_creation.toLocaleString("de")}</span></>
                        )}
                      </span>
                    </span>
                  )}
                  {compactNote && <span className="text-amber-400">· {compactNote}</span>}
                </p>
              </div>
              <TokenMeter sessionId={activeSession.id} refresh={tokenRefresh} />
              <HelpButton topic="chat" />
              <button
                onClick={handleCompact}
                disabled={compacting || activeOrphaned}
                title="Konversation jetzt zusammenfassen"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-amber-300 hover:text-amber-200 hover:bg-amber-500/10 border border-amber-500/20 hover:border-amber-500/30 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
              >
                {compacting ? <Loader2 size={12} className="animate-spin" /> : <Archive size={12} />}
                Compact
              </button>
            </div>
            {activeOrphaned && (
              <div className="mx-6 mt-4 px-4 py-3 rounded-lg border border-amber-500/30 bg-amber-500/[6%] text-sm text-amber-200 flex items-center justify-between gap-4">
                <span>Diese Session ist verwaist — der zugehörige Agent wurde gelöscht.</span>
                <button
                  onClick={() => handleDelete(activeSession.id)}
                  className="px-3 py-1 rounded-md bg-amber-500/20 hover:bg-amber-500/30 text-amber-100 text-xs whitespace-nowrap"
                >
                  Session löschen
                </button>
              </div>
            )}
            <MessageList
              messages={chat.messages}
              busy={chat.busy}
              iteration={chat.iteration}
              error={chat.error}
            />
            <MessageInput onSend={handleSend} onCancel={chat.cancel} busy={chat.busy} disabled={activeOrphaned} />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-sm text-zinc-600">
            Wähle links eine Session oder starte eine neue.
          </div>
        )}
      </main>

      <aside className="w-72 border-l border-white/[6%] bg-white/[2%] flex-shrink-0">
        <SessionList
          sessions={sessions}
          activeId={activeId}
          knownAgentIds={knownAgentIds}
          projects={projects}
          onSelect={setActiveId}
          onDelete={handleDelete}
          onNew={() => setShowNew(true)}
        />
      </aside>

      {showNew && <NewSessionDialog onClose={() => setShowNew(false)} onCreate={handleNew} />}
    </div>
  )
}
