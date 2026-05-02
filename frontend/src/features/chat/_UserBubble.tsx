import { useState } from "react"
import { Check, Clock, Copy, Pencil, Send, User, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { ImageBlock, ToolResultCard } from "./ToolCards"
import { BubbleHeader } from "./BubbleMeta"
import type { ContentBlock, Message } from "./types"

interface Props {
  message: Message
  blocks: ContentBlock[]
  isPersisted: boolean
  busy?: boolean
  onResend?: (messageId: string, newText: string) => void
}

export function UserBubble({ message, blocks, isPersisted, busy, onResend }: Props) {
  const { t } = useTranslation("chat")
  const [copied, setCopied] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState("")

  const text = blocks.find((b) => b.type === "text")?.text ?? ""
  const images = blocks.filter((b) => b.type === "image")
  const tool_results = blocks.filter((b) => b.type === "tool_result")

  const canEdit = isPersisted && !!onResend && !busy

  function copyText() {
    navigator.clipboard.writeText(text)
    setCopied(true); setTimeout(() => setCopied(false), 2000)
  }

  function submitEdit() {
    if (!onResend || !editText.trim()) return
    onResend(message.id, editText.trim()); setEditing(false)
  }

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
                <button onClick={() => { setEditText(text); setEditing(true) }} title={t("bubble.edit")}
                  className="p-1 rounded text-zinc-600 hover:text-zinc-300 transition-colors">
                  <Pencil size={11} />
                </button>
              )}
              <button onClick={copyText} title={t("bubble.copy")}
                className="p-1 rounded text-zinc-600 hover:text-zinc-300 transition-colors">
                {copied ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
              </button>
              {isPersisted
                ? <span title={t("bubble.persisted")}><Check size={11} className="text-emerald-400/60" /></span>
                : <span title={t("bubble.pending")}><Clock size={11} className="text-zinc-600" /></span>}
            </div>
          </>
        )}
        {editing && (
          <div className="space-y-1.5">
            <textarea value={editText} onChange={(e) => setEditText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submitEdit()
                if (e.key === "Escape") setEditing(false)
              }}
              autoFocus rows={Math.min(8, Math.max(2, editText.split("\n").length))}
              className="w-full px-3 py-2 rounded-2xl rounded-tr-md bg-zinc-900 border border-violet-500/40 text-sm text-zinc-100 focus:outline-none focus:ring-1 focus:ring-violet-500/60"
            />
            <div className="flex items-center justify-end gap-1.5">
              <button onClick={() => setEditing(false)} title={t("bubble.cancel")}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
                <X size={11} /> {t("bubble.cancel")}
              </button>
              <button onClick={submitEdit} disabled={!editText.trim() || editText.trim() === text}
                title={t("bubble.resend")}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] bg-gradient-to-r from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] hover:brightness-110 text-white font-medium disabled:opacity-40">
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
