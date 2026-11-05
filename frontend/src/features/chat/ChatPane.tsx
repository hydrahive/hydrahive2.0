import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { Coins, Download, FileText, GamepadIcon, GitMerge, Hammer, HelpCircle, Pencil, RotateCcw, Wand2 } from "lucide-react"
import { AgentPixelMonitor } from "./AgentPixelMonitor"
import { useAgentActivity } from "./useAgentActivity"
import { selectPixelAgents } from "./_pixelSelect"
import { AssistantRuntimeProvider } from "@assistant-ui/react"
import { chatApi } from "./api"
import { agentsApi } from "@/features/agents/api"
import { useChatCompact } from "./useChatCompact"
import { DelegationStrip } from "./DelegationStrip"
import { MessageInput } from "./MessageInput"
import { NewSessionDialog } from "./NewSessionDialog"
import { SessionList } from "./SessionList"
import { RunErrorBanner } from "./RunErrorBanner"
import { ToolConfirmBanner } from "./ToolConfirmBanner"
import { ThreePanelLayout } from "./layout/ThreePanelLayout"
import { WorkspacePanel } from "./workspace/WorkspacePanel"
import { FileOverlay } from "./workspace/FileOverlay"
import type { FileKind } from "./workspace/fileType"
import { ChatHeader } from "./_ChatHeader"
import { ChatBubbleThread } from "./_ChatBubbleThread"
import { LoadOlderSentinel } from "./_LoadOlderSentinel"
import { useMessageWindow } from "./_useMessageWindow"
import { useHydraRuntime } from "./_assistantRuntime"
import type { Message } from "./types"
import { useChat } from "./useChat"
import { CmdPill } from "@/features/buddy/_BuddyCmdPill"
import { SkillCatalogPill } from "./_SkillCatalogPill"
import { isCommand, runChatCommand } from "./commands"
import { ChatSearchProvider, useChatSearch } from "./ChatSearchContext"
import { ChatSearchBar } from "./ChatSearchBar"
import { useSessionCatalog } from "./useSessionCatalog"

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
  /** true = der Agent wurde bewusst gewählt (nicht bloß Fallback beim Laden). */
  agentSelectionExplicit?: boolean
  /** Von außen angeforderte Session in-place öffnen (z. B. Klick im Auswerten-Panel). */
  openSessionRequest?: string | null
  /** Wird aufgerufen, sobald openSessionRequest angewendet wurde (Parent kann zurücksetzen). */
  onSessionRequestHandled?: () => void
}

export function ChatPane({ deepLinkSid = null, projectId, showSidePanels = true, preferredAgentId = null, agentSelectionExplicit = false, openSessionRequest = null, onSessionRequestHandled }: ChatPaneProps) {
  const { t } = useTranslation("chat")
  const {
    agents, setAgents, projects, activeId, setActiveId, activeSession,
    activeAgent: catalogActiveAgent, visibleSessions, sessionTotal, hasMoreSessions,
    loadingMoreSessions, loadMoreSessions, loadError, refreshCatalog: loadAll,
    handleNew, handleDelete, createPreferredSession, newSessionBusy, handleSessionChanged,
  } = useSessionCatalog({
    deepLinkSid, projectId, preferredAgentId, agentSelectionExplicit,
    openSessionRequest, onSessionRequestHandled, onSessionCreated: () => setShowNew(false), t,
  })
  const [wsFile, setWsFile] = useState<{ path: string; kind: FileKind } | null>(null)
  const [showNew, setShowNew] = useState(false)
  const [localMsgs, setLocalMsgs] = useState<Message[]>([])
  const chat = useChat(activeId)
  const allMessages = useMemo(() => [...chat.messages, ...localMsgs], [chat.messages, localMsgs])
  const { windowed, hasMore, loadMore, visibleCount } = useMessageWindow(allMessages, activeId)
  const runtime = useHydraRuntime(windowed, chat.busy, chat.send, chat.cancel)
  const knownAgentIds = new Set(agents.map((agent) => agent.id))
  const buddyAgentIds = new Set(agents.filter((agent) => agent.is_buddy).map((agent) => agent.id))

  useEffect(() => { setLocalMsgs([]); chat.reload() }, [activeId, chat.reload])
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
      if (result.sessionChanged) handleSessionChanged(result.sessionChanged)
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

  const preferredAgent = preferredAgentId ? (agents.find((a) => a.id === preferredAgentId) ?? null) : null
  const activeOrphaned = activeSession ? !knownAgentIds.has(activeSession.agent_id) : false
  const activeAgent = activeSession ? catalogActiveAgent : preferredAgent

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

  const center = activeSession ? (
    <div className="flex h-full min-w-0 flex-col">
      <ChatSearchProvider messages={allMessages}>
        <ChatSearchScrollEffect />
        <div className="relative flex h-full w-full flex-col overflow-hidden bg-s-box text-[#e8eef8]">
          <div className="pointer-events-none absolute inset-0 ring-1 ring-inset ring-s-rand" />
          {searchOpen && <ChatSearchBar onClose={() => setSearchOpen(false)} />}
          <ChatHeader
            session={activeSession} agent={activeAgent} orphaned={activeOrphaned}
            compacting={compacting} compactNote={compactNote}
            lastTurnTokens={chat.lastTurnTokens} busy={chat.busy}
            systemPrompt={systemPrompt} onCompact={handleCompact}
            newSessionBusy={newSessionBusy}
            onDelete={() => handleDelete(activeSession.id)} tokenRefresh={tokenRefresh}
            onNewSession={async () => {
              if (!activeAgent) return
              await createPreferredSession()
            }}
            cockpitMode={!showSidePanels}
            sessions={!showSidePanels ? visibleSessions : undefined}
            activeSessionId={activeId}
            onSelectSession={setActiveId}
          />
          <ChatBubbleThread
            topSlot={<LoadOlderSentinel hasMore={hasMore} onLoadMore={loadMore} visibleCount={visibleCount} />}
          />
          {showPixelMonitor && (
            <AgentPixelMonitor
              agentTools={pixelData.agentTools}
              activeAgents={pixelData.activeAgents}
              doneAgents={pixelData.doneAgents}
              scope={pixelScope}
              onScope={setPixelScope}
            />
          )}
          <RunErrorBanner
            error={chat.error}
            errorKind={chat.errorKind}
            continueLabel={t("max_iter.continue_label")}
            onContinue={() => handleSend(t("max_iter.continue_send"))}
          />
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
          <DelegationStrip sessionId={activeId} busy={chat.busy} />
          <div className="border-t border-s-rand bg-s-innen">
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
    <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center text-sm text-zinc-500">
      <span>
        {preferredAgent
          ? `${preferredAgent.name} hat in diesem Projekt noch keine Session.`
          : t("session.select_or_new")}
      </span>
      <button
        type="button"
        onClick={createPreferredSession}
        disabled={agents.length === 0 || newSessionBusy}
        className="rounded-[4px] border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-xs font-black uppercase tracking-[0.12em] text-cyan-100 hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {newSessionBusy
          ? "Wird gestartet …"
          : preferredAgent ? `Session mit ${preferredAgent.name} starten` : "Neue Projekt-Session"}
      </button>
    </div>
  )

  const embeddedCenter = showSidePanels ? center : (
    <div className="flex h-full min-h-0 flex-col">
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
              onSessionChanged={handleSessionChanged}
              total={sessionTotal} hasMore={hasMoreSessions}
              loadingMore={loadingMoreSessions} onLoadMore={loadMoreSessions}
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
