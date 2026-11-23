/** Hinweis: Das Webhook-Secret wurde beim Update automatisch erzeugt (Task 44fffa23). */
import { useTranslation } from "react-i18next"

export function WebhookAutoNotice({ busy, onAck }: { busy: boolean; onAck: () => void }) {
  const { t } = useTranslation("projects")
  return (
    <div role="status" data-testid="webhook-auto-notice"
      className="space-y-2 rounded-[4px] border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
      <p className="font-medium">{t("webhook.auto_title")}</p>
      <p>{t("webhook.auto_body")}</p>
      <button type="button" onClick={onAck} disabled={busy}
        className="rounded-[4px] border border-amber-500/40 px-2 py-1 text-[11px] hover:bg-amber-500/10 disabled:opacity-50">
        {t("webhook.auto_ack")}
      </button>
    </div>
  )
}
