import { useState } from "react"
import { User, Bot, Volume2, VolumeX, Copy, Check, Clock, Code } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Markdown } from "./Markdown"
import { useVoiceOutput } from "./useVoiceOutput"
import { BubbleHeader, AssistantFooter } from "./BubbleMeta"
import { CompactionBlock } from "./CompactionBlock"
import { ImageBlock, ToolResultCard, ToolUseCard } from "./ToolCards"
import type { ContentBlock, Message } from "./types"

export function MessageBubble({ message }: { message: Message }) {
  const tts = useVoiceOutput()
  const { t } = useTranslation("chat")
  const [copied, setCopied] = useState(false)
  const [showRaw, setShowRaw] = useState(false)

  const isLive = message.id.startsWith("live-")
  const isPersisted = !message.id.startsWith("local-") && !isLive

  function copyText(text: string) {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (message.role === "compaction") {
    return <CompactionBlock message={message} />
  }

  const blocks = normalizeContent(message.content)

  if (message.role === "user") {
    const text = blocks.find((b) => b.type === "text")?.text ?? ""
    const images = blocks.filter((b) => b.type === "image")
    const tool_results = blocks.filter((b) => b.type === "tool_result")

    if (tool_results.length > 0) {
      return (
        <div className="space-y-1.5">
          {tool_results.map((tr, i) => <ToolResultCard key={i} block={tr as ContentBlock & { type: "tool_result" }} />)}
        </div>
      )
    }

    return (
      <div className="flex items-start gap-3 justify-end">
        <div className="max-w-[80%] space-y-1">
          <BubbleHeader createdAt={message.created_at} align="right" />
          {images.map((b, i) => <ImageBlock key={i} block={b as ContentBlock & { type: "image" }} />)}
          {text && (
            <>
              <div className="px-4 py-2.5 rounded-2xl rounded-tr-md bg-gradient-to-br from-indigo-600 to-violet-600 text-white text-sm whitespace-pre-wrap shadow-lg shadow-violet-900/20">
                {text}
              </div>
              <div className="flex items-center justify-end gap-1.5">
                <button
                  onClick={() => copyText(text)}
                  title={t("bubble.copy")}
                  className="p-1 rounded text-zinc-600 hover:text-zinc-300 transition-colors"
                >
                  {copied ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
                </button>
                {isPersisted
                  ? <Check size={11} className="text-emerald-400/60" title={t("bubble.persisted")} />
                  : <Clock size={11} className="text-zinc-600" title={t("bubble.pending")} />
                }
              </div>
            </>
          )}
        </div>
        <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center flex-shrink-0">
          <User size={14} className="text-zinc-400" />
        </div>
      </div>
    )
  }

  const fullText = blocks.filter((b) => b.type === "text").map((b) => b.text ?? "").join(" ")

  return (
    <div className="flex items-start gap-3">
      <div className={`w-8 h-8 rounded-full bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center flex-shrink-0 shadow-md shadow-violet-900/30 ${isLive ? "animate-pulse" : ""}`}>
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
            <button
              onClick={() => tts.speaking ? tts.stop() : tts.speak(fullText)}
              className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border transition-colors ${
                tts.speaking
                  ? "text-rose-300 bg-rose-500/15 border-rose-500/30 hover:bg-rose-500/25"
                  : "text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-zinc-200 hover:bg-white/[6%]"
              }`}
              title={tts.speaking ? t("voice.stop") : t("voice.speak")}
            >
              {tts.speaking ? <VolumeX size={12} /> : <Volume2 size={12} />}
              <span>{tts.speaking ? t("voice.stop") : t("voice.speak")}</span>
            </button>
          )}
          {fullText && (
            <button
              onClick={() => copyText(fullText)}
              title={t("bubble.copy")}
              className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-zinc-200 hover:bg-white/[6%] transition-colors"
            >
              {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
            </button>
          )}
          <button
            onClick={() => setShowRaw((r) => !r)}
            title={t("bubble.raw")}
            className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border transition-colors ${
              showRaw
                ? "text-amber-300 bg-amber-500/15 border-amber-500/30"
                : "text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-zinc-200 hover:bg-white/[6%]"
            }`}
          >
            <Code size={12} />
          </button>
        </div>
      </div>
    </div>
  )
}

function normalizeContent(content: string | ContentBlock[]): ContentBlock[] {
  if (typeof content === "string") return [{ type: "text", text: content }]
  return content
}
