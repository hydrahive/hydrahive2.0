// Fehlerbericht-Karte (docs/plans/help-error-report.md): lädt Entwurf + Status, sendet nur per Klick.
// Ohne Mailkonto der Installation schlägt der Server mailto-Daten vor; die zeigt die Karte als „Im Mailprogramm öffnen“.
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { HelpReportCardView, type ReportPhase } from "./HelpReportCardView"
import { reportApi, type ReportDraft, type ReportStatus } from "./reportApi"

export function HelpReportCard({ reportId }: { reportId: string }) {
  const navigate = useNavigate()
  const [phase, setPhase] = useState<ReportPhase>("loading")
  const [draft, setDraft] = useState<ReportDraft | null>(null)
  const [st, setSt] = useState<ReportStatus | null>(null)
  const [mailto, setMailto] = useState<{ url: string; truncated: boolean } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let alive = true
    Promise.all([reportApi.get(reportId), reportApi.status()])
      .then(([d, s]) => {
        if (!alive) return
        setDraft(d); setSt(s); setPhase("ready")
        if (d.mailto) setMailto({ url: d.mailto, truncated: !!d.truncated })   // ohne Mailkonto: fertiger Link
      })
      .catch(() => { if (alive) setPhase("gone") })        // abgelaufen, schon gesendet oder fremd
    return () => { alive = false }
  }, [reportId])

  async function send() {
    setPhase("sending"); setError(null)
    try {
      const r = await reportApi.send(reportId)
      if (r.sent) setPhase("sent")
      else { setMailto({ url: r.mailto, truncated: r.truncated }); setPhase("mailto") }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e)); setPhase("ready")
    }
  }

  async function discard() {
    try { await reportApi.discard(reportId) } catch { /* schon weg */ }
    setPhase("discarded")
  }

  async function copy() {
    if (!draft) return
    try { await navigator.clipboard.writeText(`${draft.subject}\n\n${draft.body}`); setCopied(true) } catch { setCopied(false) }
  }

  return (
    <HelpReportCardView phase={phase} subject={draft?.subject ?? ""} body={draft?.body ?? ""} to={draft?.to ?? ""}
      mailAccount={!!st?.mail_account} canSetup={!!st?.can_setup} mailto={mailto?.url} truncated={mailto?.truncated}
      error={error} copied={copied} onSend={() => void send()} onDiscard={() => void discard()}
      onCopy={() => void copy()} onSetupMail={() => navigate("/system/settings")} />
  )
}
