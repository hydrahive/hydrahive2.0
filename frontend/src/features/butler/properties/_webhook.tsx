import { useState } from "react"
import { Copy, Check } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Field, Info } from "./_helpers"

/** Projekt-Kontext des Butlers kommt über `?project=<id>` (siehe useButlerFlow). */
function projectIdFromUrl(): string | null {
  if (typeof window === "undefined") return null
  return new URLSearchParams(window.location.search).get("project")
}

export function WebhookTriggerForm() {
  const { t } = useTranslation("butler")
  const [copied, setCopied] = useState(false)
  const projectId = projectIdFromUrl()
  const webhookUrl = projectId
    ? `${window.location.origin}/api/butler/webhooks/project/${projectId}`
    : ""

  const copyUrl = () => {
    if (!webhookUrl) return
    navigator.clipboard.writeText(webhookUrl).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  if (!webhookUrl) {
    return <Info>{t("webhookNeedsProject")}</Info>
  }

  return (
    <div className="flex flex-col gap-3">
      <Field label={t("labelWebhookUrl")} hint={t("postToTrigger")}>
        <div className="flex items-center gap-1">
          <code className="flex-1 truncate rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-[11px] text-cyan-300">
            {webhookUrl}
          </code>
          <button
            type="button"
            onClick={copyUrl}
            className="shrink-0 p-1.5 rounded-lg bg-zinc-900 border border-white/15 hover:bg-white/10 transition-colors"
            title={t("copyUrl")}
          >
            {copied
              ? <Check className="h-3.5 w-3.5 text-green-400" />
              : <Copy className="h-3.5 w-3.5 text-white/40" />}
          </button>
        </div>
      </Field>
      <Info>{t("webhookSecretHint")}</Info>
    </div>
  )
}
