import { useState } from "react"
import { User, Bot, Volume2, VolumeX, Copy, Check, Clock, Code, Pencil, Send, X, RotateCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Markdown } from "./Markdown"
import { useVoiceOutput } from "./useVoiceOutput"
import { BubbleHeader, AssistantFooter } from "./BubbleMeta"
import { CompactionBlock } from "./CompactionBlock"
import { ImageBlock, ToolResultCard, ToolUseCard } from "./ToolCards"
import type { ContentBlock, Message } from "./types"

interface Props {
  message: Message
  onResend?: (messageId: string, newText: string) => void
  onRetry?: (assistantMessageId: string) => void
  busy?: boolean
}

export function MessageBubble({ message, onResend, onRetry, busy }: Props) {
  const tts = useVoiceOutput()
  const { t } = useTranslation("chat")
  const [copied, setCopied] = useState(false)
  const [showRaw, setShowRaw] = useState(false)

  const isLive = message.id.startsWith("live-")
  const isPersisted = !message.id.startsWith("local-") && !isLive
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState("")
  const canEdit = message.role === "user" && isPersisted && !!onResend && !busy

  function startEdit(currentText: string) {
    setEditText(currentText)
    setEditing(true)
  }

  function submitEdit() {
    if (!onResend || !editText.trim()) return
    onResend(message.id, editText.trim())
    setEditing(false)
  }

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
          {text && !editing && (
            <>
              <div className="px-4 py-2.5 rounded-2xl rounded-tr-md bg-gradient-to-br from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] text-white text-sm whitespace-pre-wrap shadow-lg shadow-black/30">
                {text}
              </div>
              <div className="flex items-center justify-end gap-1.5">
                {canEdit && (
                  <button
                    onClick={() => startEdit(text)}
                    title={t("bubble.edit")}
                    className="p-1 rounded text-zinc-600 hover:text-zinc-300 transition-colors"
                  >
                    <Pencil size={11} />
                  </button>
                )}
                <button
                  onClick={() => copyText(text)}
                  title={t("bubble.copy")}
                  className="p-1 rounded text-zinc-600 hover:text-zinc-300 transition-colors"
                >
                  {copied ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
                </button>
                {isPersisted
                  ? <span title={t("bubble.persisted")}><Check size={11} className="text-emerald-400/60" /></span>
                  : <span title={t("bubble.pending")}><Clock size={11} className="text-zinc-600" /></span>
                }
              </div>
            </>
          )}
          {editing && (
            <div className="space-y-1.5">
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submitEdit()
                  if (e.key === "Escape") setEditing(false)
                }}
                autoFocus
                rows={Math.min(8, Math.max(2, editText.split("\n").length))}
                className="w-full px-3 py-2 rounded-2xl rounded-tr-md bg-zinc-900 border border-violet-500/40 text-sm text-zinc-100 focus:outline-none focus:ring-1 focus:ring-violet-500/60"
              />
              <div className="flex items-center justify-end gap-1.5">
                <button
                  onClick={() => setEditing(false)}
                  title={t("bubble.cancel")}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
                >
                  <X size={11} /> {t("bubble.cancel")}
                </button>
                <button
                  onClick={submitEdit}
                  disabled={!editText.trim() || editText.trim() === text}
                  title={t("bubble.resend")}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] bg-gradient-to-r from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] hover:brightness-110 text-white font-medium disabled:opacity-40"
                >
                  <Send size={11} /> {t("bubble.resend")}
                </button>
              </div>
              <p className="text-[10px] text-zinc-600 text-right">{t("bubble.resend_hint")}</p>
            </div>
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
          {onRetry && isPersisted && !busy && (
            <button
              onClick={() => onRetry(message.id)}
              title={t("bubble.retry_hint")}
              className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] border text-zinc-400 bg-white/[3%] border-white/[8%] hover:text-violet-300 hover:bg-violet-500/10 hover:border-violet-500/30 transition-colors"
            >
              <RotateCw size={12} /> {t("bubble.retry")}
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
