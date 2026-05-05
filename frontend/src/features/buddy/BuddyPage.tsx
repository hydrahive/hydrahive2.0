import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Cpu, Dice5, HelpCircle, Loader2, RotateCcw, Save } from "lucide-react"
import { AssistantRuntimeProvider } from "@assistant-ui/react"
import { MessageInput } from "@/features/chat/MessageInput"
import { ToolConfirmBanner } from "@/features/chat/ToolConfirmBanner"
import { useChat } from "@/features/chat/useChat"
import { useHydraRuntime } from "@/features/chat/_assistantRuntime"
import { ModelPicker } from "@/features/chat/ModelPicker"
import type { Message } from "@/features/chat/types"
import { BuddyThread } from "./_BuddyThread"
import { buddyApi, type BuddyState } from "./api"
import { isCommand, runCommand } from "./commands"
import { CmdPill } from "./_BuddyCmdPill"

export function BuddyPage() {
  const { t } = useTranslation("buddy")
  const [state, setState] = useState<BuddyState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [localMsgs, setLocalMsgs] = useState<Message[]>([])
  const initRef = useRef(false)
  const chat = useChat(state?.session_id ?? null)

  const allMessages = [...chat.messages, ...localMsgs]
  const runtime = useHydraRuntime(allMessages, chat.busy, chat.send, chat.cancel)

  useEffect(() => {
    if (initRef.current) return
    initRef.current = true
    buddyApi.state()
      .then(setState)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Fehler"))
  }, [])

  useEffect(() => {
    if (state?.session_id) chat.reload()
  }, [state?.session_id, chat.reload])


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
      appendLocal("user", text)
      const result = await runCommand(text)
      appendLocal("assistant", result.message)
      if (result.newSessionId) {
        setLocalMsgs([])
        setState((s) => (s ? { ...s, session_id: result.newSessionId! } : s))
      }
      return
    }
    await chat.send(text, files)
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="text-6xl">🐝</div>
        <p className="text-sm text-rose-300">{error}</p>
      </div>
    )
  }

  if (!state) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="text-6xl animate-pulse">🐝</div>
        <Loader2 size={16} className="text-zinc-500 animate-spin" />
        <p className="text-xs text-zinc-500">{t("waking_up")}</p>
      </div>
    )
  }

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div className="flex items-center justify-center min-h-[calc(100dvh-3rem-2.5rem)] py-6">
        <div className="w-full max-w-3xl flex flex-col">
          <div
            className="relative flex flex-col rounded-[28px] border border-white/10 bg-gradient-to-b from-zinc-900/95 to-zinc-950/95 shadow-2xl shadow-[var(--hh-accent-soft)] overflow-hidden backdrop-blur"
            style={{ height: "calc(100dvh - 3rem - 2.5rem - 4rem)" }}
          >
            <div className="absolute inset-0 pointer-events-none rounded-[28px] ring-1 ring-inset ring-white/[3%]" />
            {state.created && (
              <div className="px-5 pt-3 pb-1 text-[11px] text-[var(--hh-accent-text)] text-center">
                {t("just_woken_up")}
              </div>
            )}
            <div className="px-5 py-2.5 border-b border-white/[6%] flex items-center gap-3 bg-black/30">
              <div className="text-2xl">🐝</div>
              <p className="text-sm font-medium text-zinc-100 truncate">{state.agent_name}</p>
              {state.model && (
                <ModelPicker
                  current={state.model}
                  hint="Buddy-Modell wechseln"
                  onPick={async (m) => {
                    await buddyApi.setModel(m)
                    const fresh = await buddyApi.state()
                    setState(fresh)
                  }}
                />
              )}
              <div className="flex-1" />
            </div>
            <BuddyThread />
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
                  </>
                )}
              />
            </div>
            <div className="absolute bottom-2 right-4 flex items-center gap-1.5 text-[9px] text-zinc-600">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]" />
              <span className="font-mono">ON</span>
            </div>
          </div>
          <div className="mx-auto -mt-px w-1/3 h-3 bg-gradient-to-b from-zinc-800 to-zinc-900 rounded-b-md border border-t-0 border-white/[6%]" />
          <div className="mx-auto w-2/5 h-1.5 bg-zinc-900 rounded-full mt-0.5 shadow-md shadow-black/50" />
        </div>
      </div>
    </AssistantRuntimeProvider>
  )
}
