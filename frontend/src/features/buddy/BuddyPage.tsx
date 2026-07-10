import { useEffect, useMemo, useRef, useState, type ComponentType } from "react"
import { useTranslation } from "react-i18next"
import { Cpu, Dice5, Download, FileText, GitMerge, HelpCircle, Loader2, RotateCcw, Save, Settings, Sparkles, SquarePen, Wand2 } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { AssistantRuntimeProvider } from "@assistant-ui/react"
import { MessageInput } from "@/features/chat/MessageInput"
import { HelpButton } from "@/i18n/HelpButton"
import { ToolConfirmBanner } from "@/features/chat/ToolConfirmBanner"
import { useChat } from "@/features/chat/useChat"
import { useVoiceOutput } from "@/features/chat/useVoiceOutput"
import { HydraMascot } from "@/shared/HydraMascot"
import { useHydraRuntime } from "@/features/chat/_assistantRuntime"
import { ModelPicker } from "@/features/chat/ModelPicker"
import { ProjectPicker } from "@/features/chat/ProjectPicker"
import { ReasoningEffortPill, type EffortLevel } from "@/features/chat/ReasoningEffortPill"
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
import { CockpitButton } from "@/features/cockpit/CockpitButton"
import { CockpitHeaderMenu } from "@/features/cockpit/CockpitHeaderMenu"
import { CockpitPanel } from "@/features/cockpit/CockpitPanel"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { cockpitMenu } from "@/features/cockpit/cockpitMenus"

// Buddy-Widget-Slot: installierte Module hängen Widgets ins rechte Panel ein.
// Sie bekommen onPrompt durch (→ sendet an den Buddy-Chat). Ersetzt den früheren
// fixen HealthBuddyBox-Import (lebt jetzt im patientenakte-Modul).
type BuddyWidget = ComponentType<{ onPrompt: (text: string) => void; projectId?: string | null }>
const BUDDY_WIDGETS = moduleBuddyWidgets as BuddyWidget[]

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
  const tts = useVoiceOutput()
  const mascotState = tts.speaking ? "speaking" : chat.busy ? "working" : "idle"

  const allMessages = [...chat.messages, ...localMsgs]
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
      .then(setState)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Fehler"))
  }, [])

  useEffect(() => {
    if (state?.session_id) { chat.reload(); setVisibleCount(MSG_WINDOW) }
  }, [state?.session_id, chat.reload])

  useEffect(() => {
    chatApi.listProjects().then(setProjects).catch(() => {})
  }, [])

  async function handleProjectPick(pid: string | null) {
    if (!state?.session_id) return
    setProjectBusy(true)
    try {
      await chatApi.updateSession(state.session_id, { project_id: pid ?? "" })
      setState(await buddyApi.state())
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

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <CockpitShell
        eyebrow="Buddy"
        title="Buddy-Cockpit"
        description="Dein persönlicher Agent mit Projektkontext, Modellwahl, Slash-Commands, Tools und Modul-Widgets — jetzt im gleichen Cockpit-Raster wie der Rest."
        menu={<CockpitHeaderMenu items={cockpitMenu("buddy")} />}
        actions={(
          <>
            <CockpitButton onClick={() => navigate("/buddy/settings")}>Einstellungen</CockpitButton>
            <CockpitButton
              tone="primary"
              disabled={chat.busy}
              onClick={async () => {
                const r = await buddyApi.clear()
                setLocalMsgs([])
                setReasoningEffort(null)
                setState((s) => (s ? { ...s, session_id: r.session_id } : s))
              }}
            >
              Neuer Chat
            </CockpitButton>
          </>
        )}
        className="min-h-[100dvh] bg-[#080b11]"
      >
      <div className="grid h-[calc(100dvh-156px)] min-h-[640px] gap-[10px] overflow-hidden xl:grid-cols-[280px_minmax(420px,1fr)_320px]">
        <div className="hidden min-h-0 overflow-y-auto xl:block">
          <CockpitPanel title="Buddy-Zentrale" eyebrow="Agent">
            <BuddyLeftPanel />
          </CockpitPanel>
        </div>
        <div className="flex min-w-0 flex-col min-h-0">
          <div
            className="relative flex min-h-0 flex-1 flex-col overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#0d1420] shadow-2xl shadow-black/30 backdrop-blur"
            style={{ background: "linear-gradient(158deg, rgba(105,215,255,.08), rgba(255,255,255,.015)), linear-gradient(160deg, rgba(16,78,139,.28), rgba(8,11,17,.9) 65%), #0d1420" }}
          >
            <div className="pointer-events-none absolute inset-0 rounded-[4px] ring-1 ring-inset ring-[#69d7ff]/10" />
            {state.created && (
              <div className="px-5 pt-3 pb-1 text-[11px] text-[var(--hh-accent-text)] text-center">
                {t("just_woken_up")}
              </div>
            )}
            <div className="px-5 py-2.5 border-b border-white/[6%] flex items-center gap-3 bg-black/30">
              <HydraMascot state={mascotState} size={30} animate={chat.busy || tts.speaking} />
              <p className="text-sm font-medium text-zinc-100 truncate shrink">{state.agent_name}</p>
              <ProjectPicker
                current={state.project_id}
                projects={projects}
                onPick={handleProjectPick}
                busy={projectBusy}
              />
              {state.model && (
                <div className="max-w-[9rem] min-w-0 shrink">
                  <ModelPicker
                    current={state.model}
                    hint="Buddy-Modell wechseln"
                    fullWidth
                    onPick={async (m) => {
                      await buddyApi.setModel(m)
                      const fresh = await buddyApi.state()
                      setReasoningEffort(null)
                      setState(fresh)
                    }}
                  />
                </div>
              )}
              {state.model && (
                /^(claude-|anthropic\/claude-|MiniMax-M2)/.test(state.model) && (
                  <ReasoningEffortPill
                    current={reasoningEffort}
                    extended={modelSupportsExtendedEffort(state.model, effortPrefixes)}
                    onSelect={async (effort) => {
                      if (state.session_id) {
                        await chatApi.updateSession(state.session_id, { reasoning_effort: effort })
                      }
                      setReasoningEffort(effort)
                    }}
                  />
                )
              )}
              <div className="flex-1" />
              <HelpButton topic="buddy" />
              <button
                onClick={() => navigate("/buddy/settings")}
                title={t("boxes.buddy_settings")}
                className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-white/[6%] border border-white/[8%] transition-all"
              >
                <Settings size={13} />
              </button>
              <button
                onClick={async () => {
                  const r = await buddyApi.clear()
                  setLocalMsgs([])
                  setReasoningEffort(null)
                  setState((s) => (s ? { ...s, session_id: r.session_id } : s))
                }}
                disabled={chat.busy}
                title={t("new_chat")}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/[6%] border border-white/[8%] transition-all disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <SquarePen size={11} />
                {t("new_chat")}
              </button>
            </div>
            <NewChatHint
              inputTokens={chat.lastTurnTokens?.input ?? null}
              onNewChat={async () => {
                const r = await buddyApi.clear()
                setLocalMsgs([])
                setReasoningEffort(null)
                setState((s) => (s ? { ...s, session_id: r.session_id } : s))
              }}
            />
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
            <div className="border-t border-white/[6%] bg-black/30">
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
            <div className="absolute bottom-2 right-4 flex items-center gap-1.5 text-[9px] text-zinc-600">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]" />
              <span className="font-mono">ON</span>
            </div>
          </div>
        </div>
        <div className="hidden min-h-0 flex-col gap-[10px] overflow-y-auto xl:flex">
          <CockpitPanel title="Erweiterungen" eyebrow="Buddy">
            <BuddyExtensionsPanel />
          </CockpitPanel>
          {BUDDY_WIDGETS.map((W, i) => (
            <CockpitPanel key={i} title={`Widget ${i + 1}`} eyebrow="Modul">
              <W onPrompt={(text) => handleSend(text)} projectId={state?.project_id} />
            </CockpitPanel>
          ))}
        </div>
      </div>
      </CockpitShell>
    </AssistantRuntimeProvider>
  )
}
