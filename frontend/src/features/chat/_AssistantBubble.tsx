import { useState } from "react"
import { Bot, Check, Code, Copy, RotateCw, Volume2, VolumeX } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Markdown } from "./Markdown"
import { useVoiceOutput } from "./useVoiceOutput"
import { AssistantFooter, BubbleHeader } from "./BubbleMeta"
import { ToolUseCard } from "./ToolCards"
import type { ContentBlock, Message } from "./types"

interface Props {
  message: Message
  blocks: ContentBlock[]
  isLive: boolean
  isPersisted: boolean
  busy?: boolean
  onRetry?: (assistantMessageId: string) => void
}

export function AssistantBubble({ message, blocks, isLive, isPersisted, busy, onRetry }: Props) {
  const { t } = useTranslation("chat")
  const tts = useVoiceOutput()
  const [copied, setCopied] = useState(false)
  const [showRaw, setShowRaw] = useState(false)

  const fullText = blocks.filter((b) => b.type === "text").map((b) => b.text ?? "").join(" ")

  function copyText() {
    navigator.clipboard.writeText(fullText)
    setCopied(true); setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex items-start gap-3">
      <div className={`w-8 h-8 rounded-full bg-gradient-to-br from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] flex items-center justify-center flex-shrink-0 shadow-md shadow-black/30 ${isLive ? "animate-pulse" : ""}`}>
        <Bot size={14} className="text-white" />
      </div>
      <div className="flex-1 min-w-0 space-y-2">
        <BubbleHeader createdAt={message.created_at} align="left" />
        {showRaw ? (
          <pre className="text-xs text-zinc-400 font-mono overflow-x-auto whitespace-pre-wrap bg-white/[3%] border border-white/[6%] rounded-lg p-3">
            {JSON.stringify(message.content, null, 2)}
          </pre>
        ) : (
          blocks.map((b, i) => {
            if (b.type === "text" && b.text) return <Markdown key={i} text={b.text} />
            if (b.type === "tool_use") return <ToolUseCard key={i} block={b} defaultOpen={isLive} />
            return null
          })
        )}
        <AssistantFooter metadata={message.metadata} />
        <div className="flex items-center gap-1.5 flex-wrap">
          {fullText && (
            <button onClick={() => tts.speaking ? tts.stop() : tts.speak(fullText)}
              className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border transition-colors ${
                tts.speaking
                  ? "text-rose-300 bg-rose-500/15 border-rose-500/30 hover:bg-rose-500/25"
                  : "text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-zinc-200 hover:bg-white/[6%]"
              }`}
              title={tts.speaking ? t("voice.stop") : t("voice.speak")}>
              {tts.speaking ? <VolumeX size={12} /> : <Volume2 size={12} />}
              <span>{tts.speaking ? t("voice.stop") : t("voice.speak")}</span>
            </button>
          )}
          {fullText && (
            <button onClick={copyText} title={t("bubble.copy")}
              className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-zinc-200 hover:bg-white/[6%] transition-colors">
              {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
            </button>
          )}
          {onRetry && isPersisted && !busy && (
            <button onClick={() => onRetry(message.id)} title={t("bubble.retry_hint")}
              className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-violet-300 hover:bg-violet-500/10 hover:border-violet-500/30 transition-colors">
              <RotateCw size={12} /> {t("bubble.retry")}
            </button>
          )}
          <button onClick={() => setShowRaw((r) => !r)} title={t("bubble.raw")}
            className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border transition-colors ${
              showRaw
                ? "text-amber-300 bg-amber-500/15 border-amber-500/30"
                : "text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-zinc-200 hover:bg-white/[6%]"
            }`}>
            <Code size={12} />
          </button>
        </div>
      </div>
    </div>
  )
}
