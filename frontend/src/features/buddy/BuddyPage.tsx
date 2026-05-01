import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Loader2 } from "lucide-react"
import { MessageInput } from "@/features/chat/MessageInput"
import { MessageList } from "@/features/chat/MessageList"
import { TokenMeter } from "@/features/chat/TokenMeter"
import { ToolConfirmBanner } from "@/features/chat/ToolConfirmBanner"
import { useChat } from "@/features/chat/useChat"
import { buddyApi, type BuddyState } from "./api"

export function BuddyPage() {
  const { t } = useTranslation("buddy")
  const [state, setState] = useState<BuddyState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const initRef = useRef(false)
  const chat = useChat(state?.session_id ?? null)
  const [tokenRefresh, setTokenRefresh] = useState(0)

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

  async function handleSend(text: string, files: File[] = []) {
    await chat.send(text, files)
    setTokenRefresh((n) => n + 1)
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
    <div className="flex flex-col h-[calc(100dvh-3rem-2.5rem)] -m-4 md:-m-6 max-w-3xl mx-auto w-full">
      {state.created && (
        <div className="px-6 pt-3 pb-1 text-[11px] text-[var(--hh-accent-text)]">
          {t("just_woken_up")}
        </div>
      )}

      <div className="px-6 py-2 border-b border-white/[6%] flex items-center gap-3">
        <div className="text-2xl">🐝</div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-zinc-100 truncate">{state.agent_name}</p>
          <p className="text-[10px] text-zinc-500 font-mono truncate">{state.model}</p>
        </div>
        <TokenMeter sessionId={state.session_id} refresh={tokenRefresh} />
      </div>

      <MessageList
        messages={chat.messages}
        busy={chat.busy}
        iteration={chat.iteration}
        error={chat.error}
        onResend={(id, text) => chat.send(text, [], id)}
      />

      {chat.pendingConfirm && (
        <ToolConfirmBanner
          pending={chat.pendingConfirm}
          onApprove={() => chat.confirmTool("approve")}
          onDeny={() => chat.confirmTool("deny")}
        />
      )}

      <MessageInput onSend={handleSend} onCancel={chat.cancel} busy={chat.busy} />
    </div>
  )
}
