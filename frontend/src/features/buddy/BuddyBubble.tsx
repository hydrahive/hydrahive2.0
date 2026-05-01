import { useState } from "react"
import { Check, Copy, Pencil, RotateCw, Send, Volume2, VolumeX, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Markdown } from "@/features/chat/Markdown"
import { useVoiceOutput } from "@/features/chat/useVoiceOutput"
import { CompactionBlock } from "@/features/chat/CompactionBlock"
import { ImageBlock } from "@/features/chat/ToolCards"
import type { ContentBlock, Message } from "@/features/chat/types"

interface Props {
  message: Message
  onResend?: (messageId: string, newText: string) => void
  onRetry?: (assistantMessageId: string) => void
  busy?: boolean
}

export function BuddyBubble({ message, onResend, onRetry, busy }: Props) {
  const tts = useVoiceOutput()
  const { t } = useTranslation("chat")
  const [copied, setCopied] = useState(false)
  const isLive = message.id.startsWith("live-")
  const isPersisted = !message.id.startsWith("local-") && !isLive
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState("")
  const canEdit = message.role === "user" && isPersisted && !!onResend && !busy

  function copy(text: string) {
    navigator.clipboard.writeText(text)
    setCopied(true); setTimeout(() => setCopied(false), 2000)
  }

  function submitEdit() {
    if (!onResend || !editText.trim()) return
    onResend(message.id, editText.trim())
    setEditing(false)
  }

  if (message.role === "compaction") return <CompactionBlock message={message} />

  const blocks = normalize(message.content)

  if (message.role === "user") {
    const text = blocks.find((b) => b.type === "text")?.text ?? ""
    const images = blocks.filter((b) => b.type === "image")
    const has_tool_results = blocks.some((b) => b.type === "tool_result")
    // Tool-Result-Messages sind technisches Backend-Geplauder — im Buddy ausblenden
    if (has_tool_results && !text && images.length === 0) return null
    return (
      <div className="flex items-start gap-3 justify-end">
        <div className="max-w-[80%] space-y-1 group">
          {images.map((b, i) => <ImageBlock key={i} block={b as ContentBlock & { type: "image" }} />)}
          {text && !editing && (
            <>
              <div className="px-4 py-2.5 rounded-2xl rounded-tr-md bg-gradient-to-br from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] text-white text-sm whitespace-pre-wrap shadow-md shadow-black/30">
                {text}
              </div>
              <div className="flex items-center justify-end gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                {canEdit && (
                  <button onClick={() => { setEditText(text); setEditing(true) }}
                    title={t("bubble.edit")}
                    className="p-1 rounded text-zinc-600 hover:text-zinc-300 transition-colors">
                    <Pencil size={11} />
                  </button>
                )}
                <button onClick={() => copy(text)} title={t("bubble.copy")}
                  className="p-1 rounded text-zinc-600 hover:text-zinc-300 transition-colors">
                  {copied ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
                </button>
              </div>
            </>
          )}
          {editing && (
            <div className="space-y-1.5">
              <textarea
                value={editText} onChange={(e) => setEditText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submitEdit()
                  if (e.key === "Escape") setEditing(false)
                }}
                autoFocus rows={Math.min(8, Math.max(2, editText.split("\n").length))}
                className="w-full px-3 py-2 rounded-2xl rounded-tr-md bg-zinc-900 border border-[var(--hh-accent-border)] text-sm text-zinc-100 focus:outline-none"
              />
              <div className="flex items-center justify-end gap-1.5">
                <button onClick={() => setEditing(false)}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
                  <X size={11} /> {t("bubble.cancel")}
                </button>
                <button onClick={submitEdit} disabled={!editText.trim() || editText.trim() === text}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] bg-gradient-to-r from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] hover:brightness-110 text-white font-medium disabled:opacity-40">
                  <Send size={11} /> {t("bubble.resend")}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  const fullText = blocks.filter((b) => b.type === "text").map((b) => b.text ?? "").join(" ")
  const visibleBlocks = blocks.filter((b) => b.type === "text" || b.type === "image")
  // Wenn die ganze Bubble nur tool_use ist (während Buddy arbeitet), ausblenden.
  // Live-Bubbles zeigen wir trotzdem damit Loader sichtbar bleibt.
  if (visibleBlocks.length === 0 && !isLive) return null

  return (
    <div className="flex items-start gap-3 group">
      <div className={`text-2xl flex-shrink-0 mt-0.5 ${isLive ? "animate-pulse" : ""}`}>🐝</div>
      <div className="flex-1 min-w-0 space-y-2 max-w-[85%]">
        {visibleBlocks.map((b, i) => {
          if (b.type === "text" && b.text) {
            return (
              <div key={i} className="px-4 py-2.5 rounded-2xl rounded-tl-md bg-emerald-500/[8%] border border-emerald-500/30 text-emerald-50">
                <Markdown text={b.text} />
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

function normalize(content: string | ContentBlock[]): ContentBlock[] {
  if (typeof content === "string") return [{ type: "text", text: content }]
  return content
}
