import { Info } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { AgentToolConfig, MailAccountConfig } from "./types"

interface Props {
  value: AgentToolConfig
  onChange: (next: AgentToolConfig) => void
}

type Block = "smtp" | "imap"

const inputCls =
  "w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
const labelCls = "block text-[10px] text-zinc-500"

/**
 * Geteilte SMTP/IMAP-Felder fürs „eigenes Postfach". Wird vom Agent-Editor
 * (_MailTab) UND den Buddy-Settings (_BuddySettingsMail) genutzt.
 */
export function MailAccountFields({ value, onChange }: Props) {
  const { t } = useTranslation("agents")

  function setField(block: Block, field: keyof MailAccountConfig, v: unknown) {
    onChange({ ...value, [block]: { ...(value[block] ?? {}), [field]: v } })
  }

  function setPort(block: Block, raw: string) {
    const n = raw === "" ? undefined : parseInt(raw, 10)
    setField(block, "port", Number.isNaN(n) ? undefined : n)
  }

  const smtp = value.smtp ?? {}
  const imap = value.imap ?? {}

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-1.5">
        <Info size={12} className="mt-0.5 text-zinc-600 shrink-0" />
        <p className="text-xs text-zinc-400">{t("mail.intro")}</p>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-medium text-zinc-400">{t("mail.smtp_title")}</p>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.host")}</label>
            <input className={inputCls} value={smtp.host ?? ""}
              onChange={(e) => setField("smtp", "host", e.target.value)} />
          </div>
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.port")}</label>
            <input className={inputCls} type="number" placeholder="465"
              value={smtp.port ?? ""} onChange={(e) => setPort("smtp", e.target.value)} />
          </div>
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.from")}</label>
            <input className={inputCls} value={smtp.from ?? ""} placeholder="name@domain.tld"
              onChange={(e) => setField("smtp", "from", e.target.value)} />
          </div>
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.user")}</label>
            <input className={inputCls} value={smtp.user ?? ""}
              onChange={(e) => setField("smtp", "user", e.target.value)} />
          </div>
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.password")}</label>
            <input className={inputCls} type="password" value={smtp.password ?? ""}
              placeholder={smtp.password_set ? t("mail.password_keep") : t("mail.password_placeholder")}
              onChange={(e) => setField("smtp", "password", e.target.value)} />
          </div>
          <label className="flex items-center gap-1.5 self-end pb-1 text-[11px] text-zinc-400">
            <input type="checkbox" checked={smtp.use_tls ?? true}
              onChange={(e) => setField("smtp", "use_tls", e.target.checked)} />
            {t("mail.starttls")}
          </label>
        </div>
        <p className="text-[10px] text-zinc-600">{t("mail.tls_hint")}</p>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-medium text-zinc-400">{t("mail.imap_title")}</p>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.host")}</label>
            <input className={inputCls} value={imap.host ?? ""} placeholder={t("mail.imap_host_ph")}
              onChange={(e) => setField("imap", "host", e.target.value)} />
          </div>
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.port")}</label>
            <input className={inputCls} type="number" placeholder="993"
              value={imap.port ?? ""} onChange={(e) => setPort("imap", e.target.value)} />
          </div>
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.user")}</label>
            <input className={inputCls} value={imap.user ?? ""} placeholder={t("mail.imap_login_ph")}
              onChange={(e) => setField("imap", "user", e.target.value)} />
          </div>
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.password")}</label>
            <input className={inputCls} type="password" value={imap.password ?? ""}
              placeholder={imap.password_set ? t("mail.password_keep") : t("mail.imap_login_ph")}
              onChange={(e) => setField("imap", "password", e.target.value)} />
          </div>
        </div>
      </div>
    </div>
  )
}
