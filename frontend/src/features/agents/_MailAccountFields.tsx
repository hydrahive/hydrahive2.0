import { Info } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { mailDefaultsApi } from "./api"
import type { AgentToolConfig, MailAccountConfig } from "./types"

interface Props {
  value: AgentToolConfig
  onChange: (next: AgentToolConfig) => void
}

type Block = "smtp" | "imap"

const inputCls =
  "w-full rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2 text-xs text-[#e8eef8] outline-none focus:border-[#69d7ff]/60"
const labelCls = "block text-[10px] font-semibold text-[#8d9ab0]"

/**
 * Geteilte SMTP/IMAP-Felder fürs „eigenes Postfach". Wird vom Agent-Editor
 * (_MailTab) UND den Buddy-Settings (_BuddySettingsMail) genutzt. Leere Felder
 * zeigen den globalen Account als Platzhalter (mit „(global)"-Markierung).
 */
export function MailAccountFields({ value, onChange }: Props) {
  const { t } = useTranslation("agents")
  const [defaults, setDefaults] = useState<AgentToolConfig | null>(null)

  useEffect(() => {
    mailDefaultsApi.get().then(setDefaults).catch(() => {})
  }, [])

  function setField(block: Block, field: keyof MailAccountConfig, v: unknown) {
    onChange({ ...value, [block]: { ...(value[block] ?? {}), [field]: v } })
  }

  function setPort(block: Block, raw: string) {
    const n = raw === "" ? undefined : parseInt(raw, 10)
    setField(block, "port", Number.isNaN(n) ? undefined : n)
  }

  const smtp = value.smtp ?? {}
  const imap = value.imap ?? {}
  const gd = defaults ?? {}
  const sfx = t("mail.global_suffix")
  // Globaler Wert als Platzhalter (mit „(global)"-Markierung), sonst statischer Fallback.
  function gph(v: string | number | undefined, fallback = ""): string {
    return v ? `${v}${sfx}` : fallback
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-1.5">
        <Info size={12} className="mt-0.5 text-[#718097] shrink-0" />
        <p className="text-xs text-[#8d9ab0]">{t("mail.intro")}</p>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-medium text-[#8d9ab0]">{t("mail.smtp_title")}</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.host")}</label>
            <input className={inputCls} value={smtp.host ?? ""} placeholder={gph(gd.smtp?.host)}
              onChange={(e) => setField("smtp", "host", e.target.value)} />
          </div>
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.port")}</label>
            <input className={inputCls} type="number" placeholder={gph(gd.smtp?.port, "465")}
              value={smtp.port ?? ""} onChange={(e) => setPort("smtp", e.target.value)} />
          </div>
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.from")}</label>
            <input className={inputCls} value={smtp.from ?? ""} placeholder={gph(gd.smtp?.from, "name@domain.tld")}
              onChange={(e) => setField("smtp", "from", e.target.value)} />
          </div>
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.user")}</label>
            <input className={inputCls} value={smtp.user ?? ""} placeholder={gph(gd.smtp?.user)}
              onChange={(e) => setField("smtp", "user", e.target.value)} />
          </div>
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.password")}</label>
            <input className={inputCls} type="password" value={smtp.password ?? ""}
              placeholder={smtp.password_set ? t("mail.password_keep") : t("mail.password_placeholder")}
              onChange={(e) => setField("smtp", "password", e.target.value)} />
          </div>
          <label className="flex items-center gap-1.5 self-end pb-1 text-[11px] text-[#8d9ab0]">
            <input type="checkbox" checked={smtp.use_tls ?? true}
              onChange={(e) => setField("smtp", "use_tls", e.target.checked)} />
            {t("mail.starttls")}
          </label>
        </div>
        <p className="text-[10px] text-[#718097]">{t("mail.tls_hint")}</p>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-medium text-[#8d9ab0]">{t("mail.imap_title")}</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.host")}</label>
            <input className={inputCls} value={imap.host ?? ""}
              placeholder={gph(gd.imap?.host, t("mail.imap_host_ph"))}
              onChange={(e) => setField("imap", "host", e.target.value)} />
          </div>
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.port")}</label>
            <input className={inputCls} type="number" placeholder={gph(gd.imap?.port, "993")}
              value={imap.port ?? ""} onChange={(e) => setPort("imap", e.target.value)} />
          </div>
          <div className="space-y-0.5">
            <label className={labelCls}>{t("mail.user")}</label>
            <input className={inputCls} value={imap.user ?? ""}
              placeholder={gph(gd.imap?.user, t("mail.imap_login_ph"))}
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
