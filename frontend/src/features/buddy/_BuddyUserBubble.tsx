import { useState } from "react"
import { Check, Copy, Pencil, Send, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { ImageBlock } from "@/features/chat/ToolCards"
import { extractMedia, hasMedia, MediaPreview, mediaFromBlocks } from "@/features/chat/MediaPreview"
import type { ContentBlock, Message } from "@/features/chat/types"

interface Props {
  message: Message
  blocks: ContentBlock[]
  onResend?: (messageId: string, newText: string) => void
  busy?: boolean
}

export function BuddyUserBubble({ message, blocks, onResend, busy }: Props) {
  const { t } = useTranslation("chat")
  const [copied, setCopied] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState("")
  const isPersisted = !message.id.startsWith("local-") && !message.id.startsWith("live-")
  const canEdit = isPersisted && !!onResend && !busy

  function copy(text: string) {
    navigator.clipboard.writeText(text)
    setCopied(true); setTimeout(() => setCopied(false), 2000)
  }

  function submitEdit() {
    if (!onResend || !editText.trim()) return
    onResend(message.id, editText.trim())
    setEditing(false)
  }

  const text = blocks.find((b) => b.type === "text")?.text ?? ""
  const images = blocks.filter((b) => b.type === "image")
  const tool_result_media = blocks
    .filter((b) => b.type === "tool_result")
    .map((b) => {
      const tr = b as ContentBlock & { type: "tool_result" }
      const fromBackend = mediaFromBlocks(tr.media)
      if (fromBackend.images.length + fromBackend.audio.length + fromBackend.videos.length > 0) {
        return fromBackend
      }
      return extractMedia(tr.content || "")
    })
    .filter((m) => m.images.length + m.audio.length + m.videos.length > 0)

  const has_text_only_tool_results = blocks.some((b) => b.type === "tool_result") && tool_result_media.length === 0
  if (has_text_only_tool_results && !text && images.length === 0) return null

  if (tool_result_media.length > 0 && !text && images.length === 0) {
    return (
      <div className="flex items-start gap-3">
        <div className="text-2xl flex-shrink-0 mt-0.5">🐝</div>
        <div className="flex-1 min-w-0 max-w-[85%] space-y-2">
          {tool_result_media.map((m, i) => <MediaPreview key={i} media={m} />)}
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3 justify-end">
      <div className="max-w-[80%] space-y-1 group">
        {images.map((b, i) => <ImageBlock key={i} block={b as ContentBlock & { type: "image" }} />)}
        {text && !editing && (
          <>
            <div className="px-4 py-2.5 rounded-2xl rounded-tr-md bg-amber-500/[8%] border border-amber-500/30 text-amber-50 text-sm whitespace-pre-wrap">
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
