import { useState } from "react"
import { Copy, Check } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Field } from "./_helpers"
import type { FormProps } from "./_helpers"

export function WebhookTriggerForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  const [copied, setCopied] = useState(false)
  const hookId = (params.hook_id as string) || ""
  const baseUrl = typeof window !== "undefined" ? window.location.origin : ""
  const webhookUrl = hookId ? `${baseUrl}/webhooks/butler/${hookId}` : ""

  const copyUrl = () => {
    if (!webhookUrl) return
    navigator.clipboard.writeText(webhookUrl).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const sanitize = (v: string) => v.replace(/[^a-z0-9_-]/gi, "-").toLowerCase()

  return (
    <div className="flex flex-col gap-3">
      <Field label={t("labelHookId")} hint={t("onlyAlphanumeric")}>
        <input
          type="text"
          placeholder={t("placeholderHookIdExample")}
          value={hookId}
          onChange={e => onChange({ ...params, hook_id: sanitize(e.target.value) })}
          className="w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"
        />
      </Field>
      {webhookUrl && (
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
      )}
    </div>
  )
}
