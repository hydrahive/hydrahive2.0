/* Dezenter Hinweis: Auf dem Server läuft eine neuere Version als in diesem
   Fenster. Kein Zwangs-Reload — es könnte gerade etwas eingetippt werden. */
import { RefreshCw } from "lucide-react"
import { useTranslation } from "react-i18next"

export function StaleBundleBanner() {
  const { t } = useTranslation("nav")
  return (
    <div className="flex items-center justify-center gap-3 border-b border-sky-400/20 bg-sky-500/10 px-4 py-1.5 text-xs text-sky-100">
      <span>{t("update.stale_hint")}</span>
      <button onClick={() => window.location.reload()}
        className="flex items-center gap-1 rounded-full border border-sky-300/30 px-2.5 py-0.5 hover:bg-sky-400/15">
        <RefreshCw size={11} /> {t("update.reload")}
      </button>
    </div>
  )
}
