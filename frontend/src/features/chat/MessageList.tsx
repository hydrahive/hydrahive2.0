import { useEffect, useRef } from "react"
import { Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { MessageBubble } from "./MessageBubble"
import type { Message } from "./types"

interface Props {
  messages: Message[]
  busy: boolean
  iteration: number
  error: string | null
}

export function MessageList({ messages, busy, iteration, error }: Props) {
  const { t } = useTranslation("chat")
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: "smooth" })
  }, [messages, busy])

  return (
    <div ref={ref} className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
      {messages.length === 0 && !busy && (
        <div className="flex items-center justify-center h-full text-sm text-zinc-600">
          {t("messages.empty")}
        </div>
      )}
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} />
      ))}
      {busy && (
        <div className="flex items-center gap-2 text-xs text-zinc-500 pl-11">
          <Loader2 size={12} className="animate-spin" />
          <span>{t("messages.iteration", { n: iteration })}</span>
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-rose-500/20 bg-rose-500/[6%] px-4 py-3 text-sm text-rose-300">
          {error}
        </div>
      )}
    </div>
  )
}
