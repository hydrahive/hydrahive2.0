import { useEffect, useMemo, useRef, useState, type ComponentType } from "react"
import { useTranslation } from "react-i18next"
import { Cpu, Dice5, Download, FileText, GitMerge, HelpCircle, Loader2, RotateCcw, Save, Sparkles, Wand2 } from "lucide-react"
import type { EffortLevel } from "@/features/chat/ReasoningEffortPill"
import { useNavigate } from "react-router-dom"
import { AssistantRuntimeProvider } from "@assistant-ui/react"
import { MessageInput } from "@/features/chat/MessageInput"
import { ToolConfirmBanner } from "@/features/chat/ToolConfirmBanner"
import { useChat } from "@/features/chat/useChat"
import { useVoiceOutput } from "@/features/chat/useVoiceOutput"
import { HydraMascot } from "@/shared/HydraMascot"
import { useHydraRuntime } from "@/features/chat/_assistantRuntime"
import { chatApi, type ProjectBrief } from "@/features/chat/api"
import { modelSupportsExtendedEffort, useEffortPrefixes } from "@/features/llm/effort"
import type { Message } from "@/features/chat/types"
import { BuddyThread } from "./_BuddyThread"
import { NewChatHint } from "@/features/chat/NewChatHint"
import { BuddyLeftPanel } from "./_BuddyLeftPanel"
import { BuddyExtensionsPanel } from "./_BuddyExtensionsPanel"
import { buddyApi, type BuddyState } from "./api"
import { isCommand, runCommand } from "./commands"
import { CmdPill } from "./_BuddyCmdPill"
import { moduleBuddyWidgets } from "@/modules/index.generated"
import { BuddyCockpitShell } from "./_BuddyCockpitShell"
import { BuddyCockpitHeader } from "./_BuddyCockpitHeader"
import { BuddyCockpitSlots } from "./_BuddyCockpitSlots"
import { useBuddyCockpitPrefs } from "./cockpitPrefs"

// Buddy-Widget-Slot: installierte Module hängen Widgets ins rechte Panel ein.
// Sie bekommen onPrompt durch (→ sendet an den Buddy-Chat). Ersetzt den früheren
// fixen HealthBuddyBox-Import (lebt jetzt im patientenakte-Modul).
type BuddyWidget = ComponentType<{ onPrompt: (text: string) => void; projectId?: string | null }>
const BUDDY_WIDGETS = moduleBuddyWidgets as BuddyWidget[]
const MUSIC_WIDGETS = BUDDY_WIDGETS.filter((W) => W.name.toLowerCase().includes("music"))
const OTHER_WIDGETS = BUDDY_WIDGETS.filter((W) => !W.name.toLowerCase().includes("music"))

// Nur die letzten N Nachrichten rendern — sonst hängt das UI hunderte DOM-Knoten
// (Markdown + Syntax-Highlighting) gleichzeitig auf und ruckelt. Ältere werden per
// Button/Scroll nachgeladen. ponytail: reines Slicing, kein Virtualisierungs-Framework.
const MSG_WINDOW = 60
const MSG_WINDOW_STEP = 100

export function BuddyPage() {
  const { t } = useTranslation("buddy")
  const navigate = useNavigate()
  const effortPrefixes = useEffortPrefixes()
  const [state, setState] = useState<BuddyState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reasoningEffort, setReasoningEffort] = useState<EffortLevel | null>(null)
  const [localMsgs, setLocalMsgs] = useState<Message[]>([])
  const [visibleCount, setVisibleCount] = useState(MSG_WINDOW)
  const [projects, setProjects] = useState<ProjectBrief[]>([])
  const [projectBusy, setProjectBusy] = useState(false)
  const initRef = useRef(false)
  const chat = useChat(state?.session_id ?? null)
  const { reload } = chat
  const tts = useVoiceOutput()
  const cockpit = useBuddyCockpitPrefs()
  const mascotState = tts.speaking ? "speaking" : chat.busy ? "working" : "idle"

  const allMessages = useMemo(() => [...chat.messages, ...localMsgs], [chat.messages, localMsgs])
  const windowedMessages = useMemo(
    () => (allMessages.length > visibleCount ? allMessages.slice(-visibleCount) : allMessages),
    [allMessages, visibleCount],
  )
  const hiddenCount = allMessages.length - windowedMessages.length
  const runtime = useHydraRuntime(windowedMessages, chat.busy, chat.send, chat.cancel)

  useEffect(() => {
    if (initRef.current) return
    initRef.current = true
    buddyApi.state()
      .then((s) => setState({ ...s, provider: s.provider ?? "unknown" }))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Fehler"))
  }, [])

  useEffect(() => {
    if (!state?.session_id) return
    void reload()
    const timer = setTimeout(() => setVisibleCount(MSG_WINDOW), 0)
    return () => clearTimeout(timer)
  }, [state?.session_id, reload])

  useEffect(() => {
    chatApi.listProjects().then(setProjects).catch(() => {})
  }, [])

  async function handleProjectPick(pid: string | null) {
    if (!state?.session_id) return
    setProjectBusy(true)
    try {
      await chatApi.updateSession(state.session_id, { project_id: pid ?? "" })
      const fresh = await buddyApi.state()
      setState({ ...fresh, provider: fresh.provider ?? "unknown" })
    } finally {
      setProjectBusy(false)
    }
  }

  function appendLocal(role: "user" | "assistant", text: string) {
    setLocalMsgs((prev) => [
      ...prev,
      { id: `local-cmd-${Date.now()}-${prev.length}`, role,
        content: [{ type: "text", text }],
        created_at: new Date().toISOString(), token_count: null, metadata: {} },
    ])
  }

  async function startNewChat() {
    const r = await buddyApi.clear()
    setLocalMsgs([])
    setReasoningEffort(null)
    setState((s) => (s ? { ...s, session_id: r.session_id } : s))
  }

  async function handleSend(text: string, files: File[] = []) {
    if (isCommand(text)) {
      if (!state) return
      // 1) Sofort lokal anzeigen (kein Spinner-Wartezeit für User)
      appendLocal("user", text)
      const result = await runCommand(text, state)
      appendLocal("assistant", result.message)
      if (result.newSessionId) {
        // /character + /clear: Session wechselt → localMsgs leer (sind eh
        // an die alte Session gebunden), state.session_id triggert reload.
        setLocalMsgs([])
        setState((s) => (s ? { ...s, session_id: result.newSessionId! } : s))
        return
      }
      // 2) Slash-Output dauerhaft in DB persistieren, danach localMsgs leeren
      //    und chat reload — sonst ploppt der Output nach dem nächsten reload weg.
      try {
        await buddyApi.logCmd(text, result.message)
        await chat.reload()
        setLocalMsgs([])
      } catch {
        // Persistenz failt? localMsgs bleibt — User sieht Output zumindest
        // bis zum nächsten reload.
      }
      return
    }
    await chat.send(text, files)
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <HydraMascot state="error" size={120} />
        <p className="text-sm text-rose-300">{error}</p>
      </div>
    )
  }

  if (!state) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <HydraMascot state="sleeping" size={120} animate />
        <Loader2 size={16} className="text-zinc-500 animate-spin" />
        <p className="text-xs text-zinc-500">{t("waking_up")}</p>
      </div>
    )
  }

  const usageProvider = chat.lastTurnUsage?.provider ?? state.provider
  const usageModel = chat.lastTurnUsage?.model ?? state.model
  const headerState = { ...state, provider: usageProvider, model: usageModel }
  const effortEnabled = !!state.model && /^(claude-|anthropic\/claude-|MiniMax-M2)/.test(state.model)
  const moduleWidgets = OTHER_WIDGETS.length > 0 ? (
    <div className="flex flex-col gap-3">
      {OTHER_WIDGETS.map((W, i) => (
        <W key={i} onPrompt={(text) => handleSend(text)} projectId={state.project_id} />
      ))}
    </div>
  ) : <p className="px-2 py-3 text-xs text-zinc-500">{t("cockpit.slots.no_widgets")}</p>
  const musicWidgets = MUSIC_WIDGETS.length > 0 ? (
    <div className="flex flex-col gap-3">
      {MUSIC_WIDGETS.map((W, i) => (
        <W key={i} onPrompt={(text) => handleSend(text)} projectId={state.project_id} />
      ))}
    </div>
  ) : null
  const rightRail = (
    <BuddyCockpitSlots
      prefs={cockpit.prefs}
      music={musicWidgets}
      extensions={<BuddyExtensionsPanel />}
      moduleWidgets={moduleWidgets}
      onSlotVisible={cockpit.setSlotVisible}
      onSlotCollapsed={cockpit.setSlotCollapsed}
      onRightRailCollapsed={cockpit.setRightRailCollapsed}
      onDecorVariant={cockpit.setDecorVariant}
    />
  )

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <BuddyCockpitShell
        leftRail={<BuddyLeftPanel />}
        rightRail={rightRail}
        bottomSlots={rightRail}
        decorVariant={cockpit.prefs.decorVariant}
        rightRailCollapsed={cockpit.prefs.rightRailCollapsed}
        header={(
          <BuddyCockpitHeader
            state={headerState}
            mascotState={mascotState}
            mascotAnimate={chat.busy || tts.speaking}
            projects={projects}
            projectBusy={projectBusy}
            reasoningEffort={reasoningEffort}
            effortEnabled={effortEnabled}
            extendedEffort={modelSupportsExtendedEffort(state.model, effortPrefixes)}
            busy={chat.busy}
            lastTurnTokens={chat.lastTurnTokens}
            onProjectPick={handleProjectPick}
            onModelPick={async (m) => {
              await buddyApi.setModel(m)
              const fresh = await buddyApi.state()
              setReasoningEffort(null)
              setState({ ...fresh, provider: fresh.provider ?? "unknown" })
            }}
            onEffortSelect={async (effort) => {
              if (state.session_id) await chatApi.updateSession(state.session_id, { reasoning_effort: effort })
              setReasoningEffort(effort)
            }}
            onSettings={() => navigate("/buddy/settings")}
            onNewChat={startNewChat}
          />
        )}
      >
        <NewChatHint inputTokens={chat.lastTurnTokens?.input ?? null} onNewChat={startNewChat} />
        {cockpit.error && !cockpit.loading && (
          <div className="border-b border-amber-500/20 bg-amber-500/[8%] px-5 py-1.5 text-[11px] text-amber-200">
            {t("cockpit.prefs_warning")}
          </div>
        )}
        <BuddyThread
          hiddenCount={hiddenCount}
          onLoadOlder={() => setVisibleCount((n) => n + MSG_WINDOW_STEP)}
          loadOlderLabel={t("load_older", { count: hiddenCount })}
        />
        {chat.pendingConfirm && (
          <ToolConfirmBanner
            pending={chat.pendingConfirm}
            onApprove={() => chat.confirmTool("approve")}
            onDeny={() => chat.confirmTool("deny")}
          />
        )}
        <div className="border-t border-white/[6%] bg-black/35">
          <MessageInput
            onSend={handleSend}
            onCancel={chat.cancel}
            busy={chat.busy}
            quickActions={(insert) => (
              <>
                <CmdPill icon={<HelpCircle size={11} />} label="help" color="sky" onClick={() => handleSend("/help")} />
                <CmdPill icon={<RotateCcw size={11} />} label="clear" color="amber" onClick={() => handleSend("/clear")} />
                <CmdPill icon={<Save size={11} />} label="remember" color="emerald" onClick={() => handleSend("/remember")} />
                <CmdPill icon={<Cpu size={11} />} label="model" color="violet" onClick={() => insert("/model")} />
                <CmdPill icon={<Dice5 size={11} />} label="character" color="pink" onClick={() => handleSend("/character")} />
                <CmdPill icon={<GitMerge size={11} />} label="compact" color="emerald" onClick={() => handleSend("/compact")} />
                <CmdPill icon={<Wand2 size={11} />} label="system" color="violet" onClick={() => handleSend("/system")} />
                <CmdPill icon={<FileText size={11} />} label="agent" color="emerald" onClick={() => handleSend("/agent")} />
                <CmdPill icon={<Sparkles size={11} />} label="soul" color="violet" onClick={() => handleSend("/soul")} />
                <CmdPill icon={<Download size={11} />} label="export" color="pink" onClick={() => handleSend("/export")} />
              </>
            )}
          />
        </div>
        <div className="pointer-events-none absolute bottom-2 right-4 flex items-center gap-1.5 text-[9px] text-zinc-600">
          <span className="h-1.5 w-1.5 bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]" />
          <span className="font-mono">ON</span>
        </div>
      </BuddyCockpitShell>
    </AssistantRuntimeProvider>
  )
}
