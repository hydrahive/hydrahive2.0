// Fehlerbericht-Karte im Hilfe-Fenster (docs/plans/help-error-report.md). Nur Darstellung (Props), testbar.
// Senden nur per Klick. Ohne Mailkonto: „Im Mailprogramm öffnen“ (mailto) + Link zur Mail-Einrichtung (Admin).
import { Bug, Copy, ExternalLink, Loader2, Send, Settings2, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"

export type ReportPhase = "loading" | "ready" | "sending" | "sent" | "mailto" | "discarded" | "gone" | "error"

export interface HelpReportCardViewProps {
  phase: ReportPhase
  subject: string
  body: string
  to: string
  mailAccount: boolean
  canSetup: boolean
  mailto?: string
  truncated?: boolean
  error?: string | null
  copied?: boolean
  onSend: () => void
  onDiscard: () => void
  onCopy: () => void
  onSetupMail: () => void
}

const BTN = "inline-flex items-center gap-1.5 rounded-[4px] px-2.5 py-1 text-xs font-semibold disabled:opacity-40"

export function HelpReportCardView(p: HelpReportCardViewProps) {
  const { t } = useTranslation("help")
  if (p.phase === "loading") {
    return <p className="flex items-center gap-2 text-xs text-[#9aa7bc]"><Loader2 size={12} className="animate-spin" />{t("report.loading")}</p>
  }
  if (p.phase === "gone") return <p data-help-report="gone" className="text-xs text-[#9aa7bc]">{t("report.gone")}</p>
  if (p.phase === "discarded") return <p data-help-report="discarded" className="text-xs text-[#9aa7bc]">{t("report.discarded")}</p>
  if (p.phase === "sent") {
    return <p data-help-report="sent" className="rounded-[6px] border border-emerald-400/40 bg-emerald-400/10 p-2 text-xs text-emerald-200">
      {t("report.sent", { to: p.to })}</p>
  }

  const mailtoMode = p.phase === "mailto" || !p.mailAccount
  return (
    <div data-help-report={p.phase} className="space-y-2 rounded-[6px] border border-[#69d7ff]/40 bg-s-innen p-2 text-xs text-[#d4deeb]">
      <p className="flex items-center gap-1.5 font-semibold text-[#e8eef8]"><Bug size={13} className="text-[#69d7ff]" />{t("report.title")}</p>
      <p className="text-[#9aa7bc]">{t("report.to", { to: p.to })}</p>
      <p className="break-words font-semibold">{p.subject}</p>
      <pre data-help-report-body="1" className="max-h-48 overflow-auto whitespace-pre-wrap break-words rounded-[4px] bg-s-tief p-2 font-mono text-[11px] text-[#c8d2df]">{p.body}</pre>
      {p.error && <p role="alert" className="text-red-300">{p.error}</p>}
      {mailtoMode ? (
        <div className="space-y-1.5">
          <p className="text-amber-100">{t("report.no_account")}</p>
          <div className="flex flex-wrap gap-2">
            {p.mailto && (
              <a href={p.mailto} data-help-report-mailto="1" className={`${BTN} bg-[#69d7ff] text-[#0b111c]`}>
                <ExternalLink size={12} />{t("report.open_mail")}</a>)}
            <button type="button" onClick={p.onCopy} className={`${BTN} border border-s-rand text-[#c8d2df]`}>
              <Copy size={12} />{p.copied ? t("report.copied") : t("report.copy")}</button>
          </div>
          {p.truncated && <p className="text-[#9aa7bc]">{t("report.truncated")}</p>}
          {p.canSetup
            ? <button type="button" onClick={p.onSetupMail} data-help-report-setup="1"
                className="inline-flex items-center gap-1 text-[11px] text-[#69d7ff] hover:underline">
                <Settings2 size={11} />{t("report.setup_mail")}</button>
            : <p className="text-[11px] text-[#9aa7bc]">{t("report.ask_admin")}</p>}
        </div>
      ) : (
        <div className="flex gap-2">
          <button type="button" onClick={p.onSend} disabled={p.phase === "sending"} data-help-report-send="1"
            className={`${BTN} bg-[#69d7ff] text-[#0b111c]`}>
            {p.phase === "sending" ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}{t("report.send")}</button>
          <button type="button" onClick={p.onDiscard} disabled={p.phase === "sending"} data-help-report-discard="1"
            className={`${BTN} border border-s-rand text-[#c8d2df]`}><Trash2 size={12} />{t("report.discard")}</button>
        </div>
      )}
    </div>
  )
}
