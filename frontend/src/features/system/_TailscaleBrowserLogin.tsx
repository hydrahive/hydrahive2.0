import { ExternalLink, LogIn } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminFeedback } from "@/features/cockpit/admin/ui"
import { isTailscaleLoginUrl } from "./_tailscaleLoginUrl"

interface Props {
  url: string | null
  busy: boolean
  error: string | null
  onStart: () => void
}

/** „Im Browser anmelden“: holt den Anmelde-Link und zeigt ihn an – ohne Auth-Key. */
export function TailscaleBrowserLogin({ url, busy, error, onStart }: Props) {
  const { t } = useTranslation("system")
  return (
    <div className="space-y-2" data-tailscale-browser-login>
      {!isTailscaleLoginUrl(url) ? (
        <AdminAction onClick={onStart} disabled={busy} tone="primary">
          <LogIn size={12} /> {busy ? t("tailscale.login_waiting") : t("tailscale.login_browser")}
        </AdminAction>
      ) : (
        <AdminFeedback tone="neutral">
          <p>{t("tailscale.login_open_hint")}</p>
          <a href={url} target="_blank" rel="noreferrer noopener" className="mt-1 inline-flex items-center gap-1 text-[#69d7ff] hover:underline">
            <ExternalLink size={12} /> {url}
          </a>
        </AdminFeedback>
      )}
      {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
    </div>
  )
}
