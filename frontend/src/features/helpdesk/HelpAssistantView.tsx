// Hilfe-Assistent (docs/plans/help-assistant.md): Knopf unten rechts + Fenster. Nur Darstellung (Props), testbar.
import { HelpCircle, Loader2, Send, Settings2, X } from "lucide-react"
import { useEffect, useRef } from "react"
import { useTranslation } from "react-i18next"
import { Markdown } from "@/features/chat/Markdown"
import type { HelpBubble } from "./_helpThread"

export type HelpStatus = "loading" | "ready" | "model_missing" | "error"

export interface HelpAssistantViewProps {
  open: boolean
  status: HelpStatus
  bubbles: HelpBubble[]
  sending: boolean
  draft: string
  unavailableModel?: string | null
  onToggle: () => void
  onDraft: (text: string) => void
  onSend: () => void
  onOpenLlm: () => void
}

export function HelpAssistantView(p: HelpAssistantViewProps) {
  const { t } = useTranslation("help")
  const listRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [p.bubbles])

  if (!p.open) {
    return (
      <button type="button" data-help-toggle="1" onClick={p.onToggle} title={t("helpdesk.open")}
        aria-label={t("helpdesk.open")}
        className="fixed bottom-14 right-4 z-[70] hidden h-12 w-12 sm:flex items-center justify-center rounded-full border border-[#69d7ff]/50 bg-[#13202f] text-[#69d7ff] shadow-xl hover:bg-[#1a2b3f]">
        <HelpCircle size={22} />
      </button>
    )
  }

  const canSend = p.status === "ready" && !p.sending && p.draft.trim().length > 0
  return (
    <section data-help-panel="1" role="dialog" aria-label={t("helpdesk.title")}
      className="fixed inset-0 z-[70] flex flex-col overflow-hidden bg-[#111827] shadow-2xl sm:inset-auto sm:bottom-14 sm:right-4 sm:h-[min(560px,calc(100dvh-5rem))] sm:w-[400px] sm:rounded-[8px] sm:border sm:border-[#2a364b]">
      <header className="flex items-center justify-between border-b border-[#2a364b] px-3 py-2">
        <div className="flex items-center gap-2">
          <HelpCircle size={16} className="text-[#69d7ff]" />
          <strong className="text-sm text-[#e8eef8]">{t("helpdesk.title")}</strong>
        </div>
        <button type="button" onClick={p.onToggle} aria-label={t("helpdesk.close")} title={t("helpdesk.close")}
          className="text-[#8d9ab0] hover:text-[#e8eef8]"><X size={16} /></button>
      </header>

      <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto p-3 text-sm">
        {p.status === "loading" && (
          <p className="flex items-center gap-2 text-[#8d9ab0]"><Loader2 size={14} className="animate-spin" />{t("helpdesk.loading")}</p>
        )}
        {p.status === "error" && <p data-help-error="1" className="text-red-300">{t("helpdesk.load_failed")}</p>}
        {p.status === "model_missing" && (
          <div className="space-y-3 rounded-[6px] border border-amber-300/40 bg-amber-300/10 p-3 text-amber-100">
            <p>{p.unavailableModel
              ? t("helpdesk.model_unavailable", { model: p.unavailableModel })
              : t("helpdesk.model_missing")}</p>
            <button type="button" data-help-open-llm="1" onClick={p.onOpenLlm}
              className="inline-flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-3 py-1.5 text-xs font-semibold text-[#0b111c]">
              <Settings2 size={13} /> {t("helpdesk.open_llm")}
            </button>
          </div>
        )}
        {p.status === "ready" && p.bubbles.length === 0 && (
          <p className="text-[#8d9ab0]">{t("helpdesk.welcome")}</p>
        )}
        {p.status === "ready" && p.bubbles.map((b) => <Bubble key={b.id} b={b} />)}
      </div>

      {p.status === "ready" && (
        <form className="flex items-end gap-2 border-t border-[#2a364b] p-2"
          onSubmit={(e) => { e.preventDefault(); if (canSend) p.onSend() }}>
          <textarea value={p.draft} rows={2} placeholder={t("helpdesk.placeholder")}
            onChange={(e) => p.onDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (canSend) p.onSend() } }}
            className="min-h-[2.5rem] flex-1 resize-none rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-2 py-1.5 text-sm text-[#e8eef8] outline-none focus:border-[#69d7ff]/60" />
          <button type="submit" data-help-send="1" disabled={!canSend} aria-label={t("helpdesk.send")}
            title={t("helpdesk.send")}
            className="flex h-9 w-9 items-center justify-center rounded-[4px] bg-[#69d7ff] text-[#0b111c] disabled:opacity-40">
            {p.sending ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
          </button>
        </form>
      )}
    </section>
  )
}

function Bubble({ b }: { b: HelpBubble }) {
  const { t } = useTranslation("help")
  if (b.role === "error") {
    return <p data-help-error="1" className="rounded-[6px] border border-red-400/40 bg-red-400/10 p-2 text-red-200">{b.text}</p>
  }
  if (b.role === "user") {
    return <p className="ml-8 whitespace-pre-wrap rounded-[6px] bg-[#1d3047] p-2 text-[#e8eef8]">{b.text}</p>
  }
  return (
    <div className="mr-4 rounded-[6px] bg-[#162133] p-2 text-[#d4deeb]">
      {b.text && <Markdown text={b.text} />}
      {b.busy && (
        <p className="flex items-center gap-1.5 text-xs text-[#8d9ab0]">
          <Loader2 size={12} className="animate-spin" />{t(`helpdesk.busy.${b.busy}`)}
        </p>
      )}
    </div>
  )
}
