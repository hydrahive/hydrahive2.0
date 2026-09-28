/**
 * Butler-Webhook des Projekts: URL, Secret (verdeckt) und „Neu erzeugen“.
 * Nur sichtbar, wenn der Server das Secret herausgibt (Projekt-Admin);
 * für Mitglieder mit read/write antwortet GET …/webhook mit 403 und der
 * Abschnitt bleibt weg.
 */
import { useEffect, useState, type ReactNode } from "react"
import { CheckCircle2, Copy, Eye, EyeOff, Loader2, RefreshCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "@/features/projects/api"
import type { ProjectWebhook } from "@/features/projects/types"

type Copied = "url" | "secret" | null

export function ProjectWebhookSection({ projectId }: { projectId: string }) {
  const { t } = useTranslation("projects")
  const [hook, setHook] = useState<ProjectWebhook | null>(null)
  const [visible, setVisible] = useState(false)
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState<Copied>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    projectsApi.getWebhook(projectId)
      .then((h) => { if (active) { setHook(h); setVisible(false); setError(null) } })
      .catch(() => { if (active) setHook(null) })
    return () => { active = false }
  }, [projectId])

  if (!hook) return null
  const url = `${window.location.origin}${hook.url_path}`

  async function copy(value: string, key: Exclude<Copied, null>) {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(key)
      window.setTimeout(() => setCopied(null), 1500)
    } catch {
      setError(t("webhook.copy_failed"))
    }
  }

  async function rotate() {
    if (!window.confirm(t("webhook.rotate_confirm"))) return
    setBusy(true); setError(null)
    try {
      setHook(await projectsApi.rotateWebhookSecret(projectId))
      setVisible(true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("webhook.rotate_failed"))
    } finally { setBusy(false) }
  }

  return <section className="space-y-3 border-t border-[#2a364b] pt-4">
    <div>
      <h3 className="text-sm font-medium text-[#e8eef8]">{t("webhook.title")}</h3>
      <p className="text-[11px] text-[#718097]">{t("webhook.description")}</p>
    </div>
    <Row label={t("webhook.url")} value={url} copied={copied === "url"} onCopy={() => copy(url, "url")} />
    <Row
      label={t("webhook.secret")}
      value={visible ? hook.secret : (hook.secret ? "••••••••••••••••" : t("webhook.secret_missing"))}
      copied={copied === "secret"}
      onCopy={hook.secret ? () => copy(hook.secret, "secret") : undefined}
      extra={hook.secret && (
        <button type="button" onClick={() => setVisible((v) => !v)} className="text-[#8d9ab0] hover:text-[#e8eef8]"
          title={visible ? t("webhook.hide") : t("webhook.show")}>
          {visible ? <EyeOff size={14} /> : <Eye size={14} />}
        </button>
      )}
    />
    <div className="flex items-center gap-3">
      <button type="button" onClick={rotate} disabled={busy}
        className="flex items-center gap-2 rounded-[4px] border border-[#2a364b] px-3 py-1.5 text-xs text-[#b8c4d8] hover:bg-[#1a2333] disabled:opacity-50">
        {busy ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
        {hook.secret ? t("webhook.rotate") : t("webhook.create")}
      </button>
      <span className="text-[11px] text-[#718097]">{t("webhook.header_hint")}</span>
    </div>
    {error && <p className="rounded-[4px] border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">{error}</p>}
  </section>
}

function Row({ label, value, copied, onCopy, extra }: {
  label: string; value: string; copied: boolean; onCopy?: () => void; extra?: ReactNode
}) {
  return <div className="grid grid-cols-[80px_1fr_auto] items-center gap-2">
    <span className="text-xs text-[#718097]">{label}</span>
    <code className="truncate rounded-[4px] border border-[#2a364b] bg-[#0b1220] px-2 py-1 text-[11px] text-[#b8c4d8]" title={value}>{value}</code>
    <span className="flex items-center gap-2">
      {extra}
      {onCopy && (
        <button type="button" onClick={onCopy} className="text-[#8d9ab0] hover:text-[#e8eef8]">
          {copied ? <CheckCircle2 size={14} className="text-emerald-400" /> : <Copy size={14} />}
        </button>
      )}
    </span>
  </div>
}
