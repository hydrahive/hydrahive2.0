import { useTranslation } from "react-i18next"
import { AlertTriangle } from "lucide-react"
import { isTailnetUrl } from "./_tailnetUrl"

/** Server-Kopplung läuft nur über Tailscale – andere Adressen kommen nie an (403). */
export function TailnetUrlWarning({ url }: { url: string }) {
  const { t } = useTranslation("federation")
  if (!url.trim() || isTailnetUrl(url.trim())) return null
  return (
    <p className="flex gap-1.5 text-[11px] text-amber-300">
      <AlertTriangle size={12} className="mt-0.5 shrink-0" />{t("peers.url_not_tailnet")}
    </p>
  )
}
