import { useEffect, useMemo, useRef, useState } from "react"
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
import { useEffortLevels } from "@/features/llm/effort"
import type { Message } from "@/features/chat/types"
import { NewChatHint } from "@/features/chat/NewChatHint"
import { CockpitButton } from "@/features/cockpit/CockpitButton"
import { CockpitPanel } from "@/features/cockpit/CockpitPanel"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { buddyOfflineActions, openLocalPath } from "@/features/cockpit/actionRegistry"
import { BuddyThread } from "./_BuddyThread"
import { buddyApi, type BuddyState } from "./api"
import { isCommand, runCommand } from "./commands"
import { CmdPill } from "./_BuddyCmdPill"
import { BuddyActionVisual } from "./_BuddyActionVisual"

const MSG_WINDOW = 60
const MSG_WINDOW_STEP = 100

export function BuddyPage() {
  const { t } = useTranslation("buddy")
  const navigate = useNavigate()
  const [state, setState] = useState<BuddyState | null>(null)
  const effortLevels = useEffortLevels(state?.model ?? "")
  const [error, setError] = useState<string | null>(null)
  const [reasoningEffort, setReasoningEffort] = useState<EffortLevel | null>(null)
  const [localMsgs, setLocalMsgs] = useState<Message[]>([])
  const [visibleCount, setVisibleCount] = useState(MSG_WINDOW)
  const [projects, setProjects] = useState<ProjectBrief[]>([])
  const [projectBusy, setProjectBusy] = useState(false)
  const [localOverviewOpen, setLocalOverviewOpen] = useState(false)
  const initRef = useRef(false)
  const chat = useChat(state?.session_id ?? null)
  const tts = useVoiceOutput()
  const actionActivity = chat.busy ? "working" : chat.error ? "error" : chat.lastTurnTokens ? "success" : "idle"
  const allMessages = [...chat.messages, ...localMsgs]
  const windowedMessages = useMemo(() => (allMessages.length > visibleCount ? allMessages.slice(-visibleCount) : allMessages), [allMessages, visibleCount])
  const hiddenCount = allMessages.length - windowedMessages.length
  const runtime = useHydraRuntime(windowedMessages, chat.busy, chat.send, chat.cancel)

  useEffect(() => {
    if (initRef.current) return
    initRef.current = true
    buddyApi.state().then(setState).catch((e: unknown) => setError(e instanceof Error ? e.message : "Fehler"))
  }, [])

  useEffect(() => {
    if (state?.session_id) { chat.reload(); setVisibleCount(MSG_WINDOW) }
  }, [state?.session_id, chat.reload])

  useEffect(() => { chatApi.listProjects().then(setProjects).catch(() => {}) }, [])

  const [handoverBusy, setHandoverBusy] = useState(false)

  async function newChat() {
    setHandoverBusy(true)
    try {
      const r = await buddyApi.clear()
      setLocalMsgs([])
      setReasoningEffort(null)
      setState((s) => (s ? { ...s, session_id: r.session_id } : s))
    } finally {
      setHandoverBusy(false)
    }
  }

  function handleBuddyLocalAction(actionId: string) {
    if (actionId === "today") {
      setLocalOverviewOpen((open) => !open)
      return
    }
    const action = buddyOfflineActions.find((item) => item.id === actionId)
    if (action?.path) openLocalPath(action.path)
  }

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
    setLocalMsgs((prev) => [...prev, { id: `local-cmd-${Date.now()}-${prev.length}`, role, content: [{ type: "text", text }], created_at: new Date().toISOString(), token_count: null, metadata: {} }])
  }

  async function handleSend(text: string, files: File[] = []) {
    if (isCommand(text)) {
      if (!state) return
      appendLocal("user", text)
      const result = await runCommand(text, state)
      appendLocal("assistant", result.message)
      if (result.newSessionId) {
        setLocalMsgs([])
        setState((s) => (s ? { ...s, session_id: result.newSessionId! } : s))
        return
      }
      try {
        await buddyApi.logCmd(text, result.message)
        await chat.reload()
        setLocalMsgs([])
      } catch {
        /* Log/Reload best-effort — lokale Anzeige bleibt trotzdem gültig */
      }
      return
    }
    await chat.send(text, files)
  }

  if (error) return <BuddyLoading state="error" text={error} />
  if (!state) return <BuddyLoading state="sleeping" text={t("waking_up")} loading />

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <CockpitShell className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]" title="Buddy" hideHeader>
        <CockpitTopbar active="buddy" context={state.agent_name} action={{ label: "Buddy-Settings", path: "/buddy/settings" }} />
        <div className="grid min-h-0 flex-1 gap-[10px] overflow-hidden p-[10px] xl:grid-cols-[300px_minmax(520px,1fr)_330px]">
          <BuddyLeftRail state={state} activity={actionActivity} ttsSpeaking={tts.speaking} projects={projects} localOverviewOpen={localOverviewOpen} onLocalAction={handleBuddyLocalAction} />
          <main className="panel flex min-h-0 flex-col overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#151c2b]">
            <div className="flex h-[58px] shrink-0 items-center justify-between gap-3 border-b border-[#2a364b] bg-[#111827] px-3">
              <div className="min-w-0">
                <strong className="text-sm text-[#e8eef8]">Buddy-Chat</strong>
                <div className="mt-0.5 flex flex-wrap gap-2 text-xs text-[#8d9ab0]"><span>Session: {state.session_id?.slice(0, 12) ?? "buddy"}…</span><span>· {state.model}</span></div>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <ProjectPicker current={state.project_id} projects={projects} onPick={handleProjectPick} busy={projectBusy} />
                {state.model && <div className="w-[210px]"><ModelPicker current={state.model} hint="Buddy-Modell wechseln" fullWidth onPick={async (m) => { await buddyApi.setModel(m); setReasoningEffort(null); setState(await buddyApi.state()) }} /></div>}
                {effortLevels.length > 0 && <ReasoningEffortPill current={reasoningEffort} levels={effortLevels} onSelect={async (effort) => { if (state.session_id) await chatApi.updateSession(state.session_id, { reasoning_effort: effort ?? "" }); setReasoningEffort(effort) }} />}
                <HelpButton topic="buddy" />
                <CockpitButton disabled={chat.busy || handoverBusy} tone="primary" onClick={newChat}>{handoverBusy ? "Übergabe wird erstellt …" : "Neuer Chat"}</CockpitButton>
              </div>
            </div>
            {state.created && <div className="px-5 pt-3 pb-1 text-center text-[11px] text-[#69d7ff]">{t("just_woken_up")}</div>}
            <NewChatHint inputTokens={chat.lastTurnTokens?.input ?? null} onNewChat={newChat} />
            <BuddyThread hiddenCount={hiddenCount} onLoadOlder={() => setVisibleCount((n) => n + MSG_WINDOW_STEP)} loadOlderLabel={t("load_older", { count: hiddenCount })} />
            {chat.pendingConfirm && <ToolConfirmBanner pending={chat.pendingConfirm} onApprove={() => chat.confirmTool("approve")} onDeny={() => chat.confirmTool("deny")} />}
            <div className="shrink-0 border-t border-[#2a364b] bg-[#111827]">
              <MessageInput onSend={handleSend} onCancel={chat.cancel} busy={chat.busy} quickActions={(insert) => <BuddyQuickActions handleSend={handleSend} insert={insert} />} />
            </div>
          </main>
          <BuddyRightRail state={state} onSettings={() => navigate("/buddy/settings")} />
        </div>
      </CockpitShell>
    </AssistantRuntimeProvider>
  )
}

function BuddyLoading({ state, text, loading }: { state: "error" | "sleeping"; text: string; loading?: boolean }) {
  return <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3"><HydraMascot state={state} size={120} animate={loading} />{loading && <Loader2 size={16} className="animate-spin text-zinc-500" />}<p className="text-sm text-zinc-400">{text}</p></div>
}

function BuddyLeftRail({ state, activity, ttsSpeaking, projects, localOverviewOpen, onLocalAction }: { state: BuddyState; activity: "idle" | "working" | "success" | "error"; ttsSpeaking: boolean; projects: ProjectBrief[]; localOverviewOpen: boolean; onLocalAction: (actionId: string) => void }) {
  const activeProject = projects.find((project) => project.id === state.project_id)
  return <aside className="hidden min-h-0 overflow-y-auto xl:block"><CockpitPanel title="Buddy" eyebrow="Companion"><div className="rounded-[4px] border border-[#2a364b] bg-[#070b12] p-3"><div className="grid h-[160px] place-items-center overflow-hidden rounded-[4px] border border-[#2a364b] bg-[radial-gradient(circle_at_50%_20%,rgba(244,114,182,.25),rgba(8,11,17,.9))]"><BuddyActionVisual activity={activity} speaking={ttsSpeaking} /></div><div className="mt-2 text-xs text-[#8d9ab0]">Reaction: {ttsSpeaking ? "spricht" : activity === "working" ? "arbeitet" : activity === "error" ? "Fehler" : activity === "success" ? "gelungen" : "wach"}</div></div><div className="mt-4 space-y-3"><label className="block text-xs font-bold uppercase tracking-[0.12em] text-[#69d7ff]">Modus</label><select className="w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]"><option>Normaler Buddy-Chat</option><option>Fokus</option><option>Humorvoll</option><option>Kurze Antworten</option></select><div className="space-y-2">{buddyOfflineActions.map((action) => <button key={action.id} onClick={() => onLocalAction(action.id)} className="w-full rounded-[4px] border border-[#2a364b] bg-[#111827] p-2 text-left text-sm text-[#e8eef8] hover:border-[#46617f]">{action.label}<span className="block text-xs text-[#8d9ab0]">{action.description}</span></button>)}</div>{localOverviewOpen && <div className="rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-2 text-xs leading-4 text-[#8d9ab0]"><strong className="block text-[#e8eef8]">Lokale Übersicht</strong><span>Projekt: {activeProject?.name ?? "kein Projekt gewählt"}</span><br /><span>Geladene Projekte: {projects.length}</span><br /><span>Agent: {state.agent_name}</span></div>}<p className="text-xs text-[#8d9ab0]">Agent: {state.agent_name}</p></div></CockpitPanel></aside>
}

function BuddyRightRail({ state, onSettings }: { state: BuddyState; onSettings: () => void }) {
  const primaryLinks = [["Projekte", "/projects"], ["Media", "/media"], ["Vault", "/vault"], ["Admin", "/admin"]]
  const toolLinks = [["Scratchpad", "/scratchpad"], ["Musik", "/musicplayer"], ["Spiele", "/minigames"], ["Boardgames", "/boardgames"]]

  return <aside className="hidden min-h-0 overflow-y-auto xl:block"><CockpitPanel title="Kontext" eyebrow="Ruhig" actions={<button onClick={onSettings} className="rounded-[4px] border border-[#2a364b] p-1 text-[#8d9ab0] hover:text-[#e8eef8]"><Settings size={14} /></button>}><div className="rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-3"><div className="text-[11px] uppercase tracking-[0.12em] text-[#69d7ff]">Aktiver Buddy</div><div className="mt-1 text-sm font-bold text-[#e8eef8]">{state.agent_name}</div><div className="mt-1 text-xs text-[#8d9ab0]">Module bleiben im Hintergrund. Buddy bleibt zuerst Chat und Companion.</div></div><div className="mt-3 grid grid-cols-2 gap-2">{primaryLinks.map(([label, path]) => <button key={path} onClick={() => openLocalPath(path)} className="rounded-[4px] border border-[#2a364b] bg-[#111827] p-2 text-left text-xs font-bold text-[#e8eef8] hover:border-[#46617f]">{label}</button>)}</div></CockpitPanel><CockpitPanel title="Werkzeuge" eyebrow="Kompakt"><p className="text-xs leading-4 text-[#8d9ab0]">Keine Modul-Boxen im Buddy. Häufige Werkzeuge liegen hier als leise Links; die vollständige Verwaltung bleibt in den Cockpits.</p><div className="mt-3 flex flex-wrap gap-2">{toolLinks.map(([label, path]) => <button key={path} onClick={() => openLocalPath(path)} className="rounded-full border border-[#2a364b] bg-[#111827] px-3 py-1 text-xs text-[#e8eef8] hover:border-[#46617f]">{label}</button>)}</div></CockpitPanel><CockpitPanel title="Hinweis" eyebrow="Offline"><p className="text-xs leading-4 text-[#8d9ab0]">Diese Spalte startet keine LLM-Anfrage. Für Module: Cockpit öffnen, dort arbeiten, bei Bedarf bewusst Buddy fragen.</p></CockpitPanel></aside>
}

function BuddyQuickActions({ handleSend, insert }: { handleSend: (text: string) => void; insert: (text: string) => void }) {
  return <><CmdPill icon={<HelpCircle size={11} />} label="help" color="sky" onClick={() => handleSend("/help")} /><CmdPill icon={<RotateCcw size={11} />} label="clear" color="amber" onClick={() => handleSend("/clear")} /><CmdPill icon={<Save size={11} />} label="remember" color="emerald" onClick={() => handleSend("/remember")} /><CmdPill icon={<Cpu size={11} />} label="model" color="violet" onClick={() => insert("/model")} /><CmdPill icon={<Dice5 size={11} />} label="character" color="pink" onClick={() => handleSend("/character")} /><CmdPill icon={<GitMerge size={11} />} label="compact" color="emerald" onClick={() => handleSend("/compact")} /><CmdPill icon={<Wand2 size={11} />} label="system" color="violet" onClick={() => handleSend("/system")} /><CmdPill icon={<FileText size={11} />} label="agent" color="emerald" onClick={() => handleSend("/agent")} /><CmdPill icon={<Sparkles size={11} />} label="soul" color="violet" onClick={() => handleSend("/soul")} /><CmdPill icon={<Download size={11} />} label="export" color="pink" onClick={() => handleSend("/export")} /><CmdPill icon={<SquarePen size={11} />} label="idea" color="sky" onClick={() => insert("Idee merken:")} /></>
}
