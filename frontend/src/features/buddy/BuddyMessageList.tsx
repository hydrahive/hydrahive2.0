import { useEffect, useRef } from "react"
import { useTranslation } from "react-i18next"
import { BuddyBubble } from "./BuddyBubble"
import type { ContentBlock, Message } from "@/features/chat/types"

interface Props {
  messages: Message[]
  busy: boolean
  error: string | null
  onResend?: (messageId: string, newText: string) => void
}

export function BuddyMessageList({ messages, busy, error, onResend }: Props) {
  const { t } = useTranslation("buddy")
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" })
  }, [messages, busy])

  function retryAssistant(assistantId: string) {
    if (!onResend) return
    const idx = messages.findIndex((m) => m.id === assistantId)
    if (idx <= 0) return
    for (let i = idx - 1; i >= 0; i--) {
      if (messages[i].role !== "user") continue
      const text = extractText(messages[i].content)
      if (!text) continue
      onResend(messages[i].id, text)
      return
    }
  }

  return (
    <div ref={ref} className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
      {messages.length === 0 && !busy && (
        <div className="flex flex-col items-center justify-center h-full gap-2 text-center">
          <div className="text-5xl">🐝</div>
          <p className="text-sm text-zinc-500">{t("empty_hint")}</p>
        </div>
      )}
      {messages.map((m) => (
        <BuddyBubble key={m.id} message={m} onResend={onResend} onRetry={retryAssistant} busy={busy} />
      ))}
      {busy && (
        <div className="flex items-center gap-2 pl-11">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--hh-accent)] animate-pulse" />
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--hh-accent)] animate-pulse" style={{ animationDelay: "0.15s" }} />
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--hh-accent)] animate-pulse" style={{ animationDelay: "0.3s" }} />
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-rose-500/20 bg-rose-500/[6%] px-3 py-2 text-xs text-rose-300">
          {error}
        </div>
      )}
    </div>
  )
}

function extractText(content: string | ContentBlock[]): string {
  if (typeof content === "string") return content
  for (const b of content) if (b.type === "text" && b.text) return b.text
  return ""
}
