import { useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Coins, Download, FileText, GamepadIcon, GitMerge, Hammer, HelpCircle, Pencil, RotateCcw, Wand2 } from "lucide-react"
import { AgentPixelMonitor } from "./AgentPixelMonitor"
import { useAgentActivity } from "./useAgentActivity"
import { selectPixelAgents } from "./_pixelSelect"
import { AssistantRuntimeProvider } from "@assistant-ui/react"
import { chatApi } from "./api"
import { agentsApi } from "@/features/agents/api"
import { useChatCompact } from "./useChatCompact"
import { MessageInput } from "./MessageInput"
import { NewSessionDialog } from "./NewSessionDialog"
import { SessionList } from "./SessionList"
import { ToolConfirmBanner } from "./ToolConfirmBanner"
import { ThreePanelLayout } from "./layout/ThreePanelLayout"
import { WorkspacePanel } from "./workspace/WorkspacePanel"
import { FileOverlay } from "./workspace/FileOverlay"
import type { FileKind } from "./workspace/fileType"
import { ChatHeader } from "./_ChatHeader"
import { ChatBubbleThread } from "./_ChatBubbleThread"
import { useHydraRuntime } from "./_assistantRuntime"
import type { AgentBrief, Message, Session } from "./types"
import type { ProjectBrief } from "./api"
import { useChat } from "./useChat"
import { CmdPill } from "@/features/buddy/_BuddyCmdPill"
import { SkillCatalogPill } from "./_SkillCatalogPill"
import { isCommand, runChatCommand } from "./commands"
import { ChatSearchProvider, useChatSearch } from "./ChatSearchContext"
import { ChatSearchBar } from "./ChatSearchBar"

function ChatSearchScrollEffect() {
  const { activeMessageId } = useChatSearch()
  useEffect(() => {
    if (!activeMessageId) return
    const el = document.querySelector(`[data-msg-id="${activeMessageId}"]`)
    el?.scrollIntoView({ behavior: "smooth", block: "center" })
  }, [activeMessageId])
  return null
}

interface ChatPaneProps {
  deepLinkSid?: string | null
  /** undefined = alle Sessions; null = nur sessions ohne Projekt; string = Projekt-Sessions */
  projectId?: string | null
  showSidePanels?: boolean
  preferredAgentId?: string | null
}

export function ChatPane({ deepLinkSid = null, projectId, showSidePanels = true, preferredAgentId = null }: ChatPaneProps) {
  const { t } = useTranslation("chat")
  const deepLinkApplied = useRef(false)

  const [wsFile, setWsFile] = useState<{ path: string; kind: FileKind } | null>(null)
  const [sessions, setSessions] = useState<Session[]>([])
  const [agents, setAgents] = useState<AgentBrief[]>([])
  const [projects, setProjects] = useState<ProjectBrief[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [showNew, setShowNew] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [localMsgs, setLocalMsgs] = useState<Message[]>([])
  const chat = useChat(activeId)
  const allMessages = useMemo(() => [...chat.messages, ...localMsgs], [chat.messages, localMsgs])
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
      setLoadError(null)
      const visibleSessions = projectId === undefined ? s : s.filter((session) => session.project_id === projectId)
      if (!deepLinkApplied.current && deepLinkSid) {
        deepLinkApplied.current = true
        setActiveId(deepLinkSid)
      } else if (!activeId && !deepLinkSid && visibleSessions.length > 0) {
        setActiveId(visibleSessions[0].id)
      }
    } catch {
      // Nicht still schlucken (#211): die Sitzungsliste wäre sonst unbemerkt veraltet.
      setLoadError("Sitzungen konnten nicht geladen werden — Anzeige ist evtl. veraltet.")
    }
  }

  // Einmalig beim Mount laden — loadAll bewusst nicht in den Deps (sonst Re-Run pro Render).
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadAll() }, [])
  useEffect(() => { setLocalMsgs([]); chat.reload() }, [activeId, chat.reload])
  useEffect(() => {
    if (projectId === undefined || !activeId) return
    const current = sessions.find((s) => s.id === activeId)
    if (current && current.project_id !== projectId) setActiveId(null)
  }, [projectId, activeId, sessions])

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
  const [showPixelMonitor, setShowPixelMonitor] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "f" && activeId) {
        const target = e.target as HTMLElement
        if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return
        e.preventDefault()
        setSearchOpen(true)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [activeId])

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
      const result = await runChatCommand(text, activeSession, activeAgent, chat.messages)
      if (result.sendToAgent) {
        await chat.send(result.sendToAgent, files)
        loadAll(); setTokenRefresh((n) => n + 1)
        return
      }
      appendLocal("user", text)
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

  const visibleSessions = useMemo(
    () => projectId === undefined ? sessions : sessions.filter((session) => session.project_id === projectId),
    [sessions, projectId],
  )
  const activeSession = visibleSessions.find((s) => s.id === activeId) ?? null
  const preferredAgent = preferredAgentId ? (agents.find((a) => a.id === preferredAgentId) ?? null) : null
  const activeOrphaned = activeSession ? !knownAgentIds.has(activeSession.agent_id) : false
  const activeAgent = activeSession ? (agents.find((a) => a.id === activeSession.agent_id) ?? null) : preferredAgent

  useEffect(() => {
    if (activeId || deepLinkSid || visibleSessions.length === 0) return
    setActiveId(visibleSessions[0].id)
  }, [activeId, deepLinkSid, visibleSessions])

  const [pixelScope, setPixelScope] = useState<"chat" | "all">("chat")
  const { running, doneNames } = useAgentActivity(showPixelMonitor)
  const pixelData = useMemo(() => {
    // ask_agent-Ziele dieser Session → für die „Chat"-Scope-Filterung
    const askTargets: string[] = []
    for (const msg of allMessages) {
      if (!Array.isArray(msg.content)) continue
      for (const block of msg.content) {
        const b = block as { type?: string; name?: string; input?: { agent_id?: string } }
        if (b.type !== "tool_use" || b.name !== "ask_agent") continue
        const tid = b.input?.agent_id ?? ""
        if (tid) askTargets.push(tid)
        const found = agents.find(a => a.id === tid || a.name.toLowerCase().includes(tid.toLowerCase()))
        if (found?.name) askTargets.push(found.name)
        if (found?.id) askTargets.push(found.id)
      }
    }
    return selectPixelAgents(running, pixelScope, activeAgent?.name ?? null, askTargets, doneNames)
  }, [running, doneNames, pixelScope, activeAgent, agents, allMessages])

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

  const handleSessionChanged = (updated: Session) =>
    setSessions((cur) => cur.map((s) => s.id === updated.id ? updated : s))
  const handleAgentChanged = (updated: AgentBrief) =>
    setAgents((cur) => cur.map((a) => a.id === updated.id ? updated : a))

  async function createPreferredSession() {
    const agent = activeAgent ?? preferredAgent ?? agents.find((a) => !a.is_buddy) ?? agents[0]
    if (!agent) return
    const s = await chatApi.createSession(agent.id, undefined, projectId ?? undefined)
    setSessions((cur) => [s, ...cur])
    setActiveId(s.id)
  }

  const center = activeSession ? (
    <div className="flex h-full min-w-0 flex-col">
      <ChatSearchProvider messages={allMessages}>
        <ChatSearchScrollEffect />
        <div className="relative flex h-full w-full flex-col overflow-hidden bg-[#151c2b] text-[#e8eef8]">
          <div className="pointer-events-none absolute inset-0 ring-1 ring-inset ring-[#2a364b]" />
          {searchOpen && <ChatSearchBar onClose={() => setSearchOpen(false)} />}
          <ChatHeader
            session={activeSession} agent={activeAgent} orphaned={activeOrphaned}
            compacting={compacting} compactNote={compactNote}
            lastTurnTokens={chat.lastTurnTokens} busy={chat.busy}
            systemPrompt={systemPrompt} onCompact={handleCompact}
            onDelete={() => handleDelete(activeSession.id)} tokenRefresh={tokenRefresh}
            onNewSession={async () => {
              if (!activeAgent) return
              await createPreferredSession()
            }}
          />
          <ChatBubbleThread />
          {showPixelMonitor && (
            <AgentPixelMonitor
              agentTools={pixelData.agentTools}
              activeAgents={pixelData.activeAgents}
              doneAgents={pixelData.doneAgents}
              scope={pixelScope}
              onScope={setPixelScope}
            />
          )}
          {chat.error && (
            <div className="px-4 py-2 text-xs text-rose-400 bg-rose-500/10 border-t border-rose-500/20 flex items-center justify-between gap-3">
              <span>{chat.error}</span>
              {chat.errorKind === "max_iterations" && (
                <button
                  onClick={() => handleSend(t("max_iter.continue_send"))}
                  className="px-2 py-1 rounded-md text-xs text-rose-200 bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 whitespace-nowrap"
                >
                  {t("max_iter.continue_label")}
                </button>
              )}
            </div>
          )}
          {chat.pendingConfirm && (
            <ToolConfirmBanner
              pending={chat.pendingConfirm}
              onApprove={() => chat.confirmTool("approve")}
              onDeny={() => chat.confirmTool("deny")}
            />
          )}
          {chat.compacting && (
            <div className="px-4 py-1.5 text-xs text-amber-400/80 bg-amber-500/5 border-t border-amber-500/15 flex items-center gap-2">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400/60 animate-pulse" />
              Kontext wird komprimiert…
            </div>
          )}
          <div className="border-t border-[#2a364b] bg-[#111827]">
            <MessageInput
              onSend={handleSend} onCancel={chat.cancel}
              busy={chat.busy} disabled={activeOrphaned}
              quickActions={(insert) => (
                <>
                  <CmdPill icon={<HelpCircle size={11} />} label="help" color="sky" onClick={() => handleSend("/help")} />
                  <CmdPill icon={<RotateCcw size={11} />} label="clear" color="amber" onClick={() => handleSend("/clear")} />
                  <CmdPill icon={<GitMerge size={11} />} label="compact" color="emerald" onClick={() => handleSend("/compact")} />
                  <CmdPill icon={<Coins size={11} />} label="tokens" color="amber" onClick={() => handleSend("/tokens")} />
                  <CmdPill icon={<Pencil size={11} />} label="title" color="pink" onClick={() => insert("/title ")} />
                  <CmdPill icon={<Wand2 size={11} />} label="system" color="violet" onClick={() => handleSend("/system")} />
                  <CmdPill icon={<Hammer size={11} />} label="tools" color="sky" onClick={() => handleSend("/tools")} />
                  <CmdPill icon={<FileText size={11} />} label="agent" color="emerald" onClick={() => handleSend("/agent")} />
                  <CmdPill icon={<Download size={11} />} label="export" color="pink" onClick={() => handleSend("/export")} />
                  <SkillCatalogPill agentId={activeAgent?.id ?? null} insert={insert} />
                  <CmdPill icon={<GamepadIcon size={11} />} label="pixel" color={showPixelMonitor ? "violet" : "sky"} onClick={() => setShowPixelMonitor(v => !v)} />
                </>
              )}
            />
          </div>
        </div>
      </ChatSearchProvider>
    </div>
  ) : (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-sm text-zinc-600">
      <span>{t("session.select_or_new")}</span>
      <button
        type="button"
        onClick={createPreferredSession}
        disabled={agents.length === 0}
        className="rounded-[4px] border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-xs font-black uppercase tracking-[0.12em] text-cyan-100 hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Neue Projekt-Session
      </button>
    </div>
  )

  const embeddedCenter = showSidePanels ? center : (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 items-center gap-2 overflow-x-auto border-b border-[#2a364b] bg-[#121a29] px-3 py-2">
        {visibleSessions.map((session) => (
          <button
            key={session.id}
            type="button"
            onClick={() => setActiveId(session.id)}
            className={[
              "max-w-48 shrink-0 truncate rounded-[4px] border px-2.5 py-1.5 text-xs font-semibold transition-colors",
              session.id === activeId
                ? "border-[#69d7ff]/45 bg-[#1c2940] text-[#69d7ff]"
                : "border-[#2a364b] bg-[#0d1420] text-[#8d9ab0] hover:border-[#46617f] hover:text-[#e8eef8]",
            ].join(" ")}
          >
            {session.title || "Neue Session"}
          </button>
        ))}
        <button
          type="button"
          onClick={createPreferredSession}
          disabled={agents.length === 0}
          className="shrink-0 rounded-[4px] border border-transparent bg-gradient-to-br from-[#1fb6ff] to-[#8b5cf6] px-2.5 py-1.5 text-xs font-black uppercase tracking-[0.10em] text-white hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Session +
        </button>
      </div>
      <div className="min-h-0 flex-1">{center}</div>
    </div>
  )

  return (
    <AssistantRuntimeProvider runtime={runtime} key={activeId ?? "empty"}>
      {showSidePanels ? (
        <ThreePanelLayout
          left={
            <SessionList
              sessions={visibleSessions} activeId={activeId}
              knownAgentIds={knownAgentIds} buddyAgentIds={buddyAgentIds} projects={projects}
              onSelect={setActiveId} onDelete={handleDelete} onNew={() => setShowNew(true)}
              activeSession={activeSession} activeAgent={activeAgent}
              onSessionChanged={handleSessionChanged} onAgentChanged={handleAgentChanged}
            />
          }
          center={embeddedCenter}
          right={<WorkspacePanel agentId={activeAgent?.id ?? null} projectId={activeSession?.project_id} onOpenFile={(path, kind) => setWsFile({ path, kind })} />}
        />
      ) : embeddedCenter}
      {wsFile && activeAgent && (
        <FileOverlay agentId={activeAgent.id} path={wsFile.path} kind={wsFile.kind} onClose={() => setWsFile(null)} />
      )}
      {showNew && <NewSessionDialog onClose={() => setShowNew(false)} onCreate={handleNew} />}
      {loadError && (
        <div className="fixed bottom-4 right-4 z-50 max-w-sm px-4 py-3 rounded-xl bg-rose-950/90 border border-rose-500/40 text-xs text-rose-200 shadow-xl backdrop-blur flex items-center gap-3">
          <span>{loadError}</span>
          <button
            onClick={() => loadAll()}
            className="px-2 py-1 rounded-md bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 whitespace-nowrap"
          >
            {t("retry", "Erneut")}
          </button>
        </div>
      )}
    </AssistantRuntimeProvider>
  )
}
