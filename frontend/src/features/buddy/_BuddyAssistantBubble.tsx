import { useState } from "react"
import { Check, Copy, RotateCw, Volume2, VolumeX } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Markdown } from "@/features/chat/Markdown"
import { useVoiceOutput } from "@/features/chat/useVoiceOutput"
import { ImageBlock } from "@/features/chat/ToolCards"
import { extractMedia, hasMedia, MediaPreview } from "@/features/chat/MediaPreview"
import type { ContentBlock, Message } from "@/features/chat/types"

interface Props {
  message: Message
  blocks: ContentBlock[]
  onRetry?: (assistantMessageId: string) => void
  busy?: boolean
}

export function BuddyAssistantBubble({ message, blocks, onRetry, busy }: Props) {
  const { t } = useTranslation("chat")
  const tts = useVoiceOutput()
  const [copied, setCopied] = useState(false)
  const isLive = message.id.startsWith("live-")
  const isPersisted = !message.id.startsWith("local-") && !isLive

  function copy(text: string) {
    navigator.clipboard.writeText(text)
    setCopied(true); setTimeout(() => setCopied(false), 2000)
  }

  const fullText = blocks.filter((b) => b.type === "text").map((b) => b.text ?? "").join(" ")
  const visibleBlocks = blocks.filter((b) => b.type === "text" || b.type === "image")
  if (visibleBlocks.length === 0 && !isLive) return null

  return (
    <div className="flex items-start gap-3 group">
      <div className={`text-2xl flex-shrink-0 mt-0.5 ${isLive ? "animate-pulse" : ""}`}>🐝</div>
      <div className="flex-1 min-w-0 space-y-2 max-w-[85%]">
        {visibleBlocks.map((b, i) => {
          if (b.type === "text" && b.text) {
            const media = extractMedia(b.text)
            return (
              <div key={i} className="space-y-2">
                <div className="px-4 py-2.5 rounded-2xl rounded-tl-md bg-emerald-500/[8%] border border-emerald-500/30 text-emerald-50">
                  <Markdown text={b.text} />
                </div>
                {hasMedia(b.text) && <MediaPreview media={media} />}
              </div>
            )
          }
          if (b.type === "image") {
            return <ImageBlock key={i} block={b as ContentBlock & { type: "image" }} />
          }
          return null
        })}
        <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
          {fullText && (
            <button
              onClick={() => tts.speaking ? tts.stop() : tts.speak(fullText)}
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] transition-colors ${
                tts.speaking
                  ? "text-rose-300 bg-rose-500/15"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[5%]"
              }`}
              title={tts.speaking ? t("voice.stop") : t("voice.speak")}
            >
              {tts.speaking ? <VolumeX size={10} /> : <Volume2 size={10} />}
            </button>
          )}
          {fullText && (
            <button onClick={() => copy(fullText)} title={t("bubble.copy")}
              className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] text-zinc-500 hover:text-zinc-300 hover:bg-white/[5%] transition-colors">
              {copied ? <Check size={10} className="text-emerald-400" /> : <Copy size={10} />}
            </button>
          )}
          {onRetry && isPersisted && !busy && (
            <button onClick={() => onRetry(message.id)} title={t("bubble.retry_hint")}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] text-zinc-500 hover:text-[var(--hh-accent-text)] hover:bg-[var(--hh-accent-soft)] transition-colors">
              <RotateCw size={10} />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
