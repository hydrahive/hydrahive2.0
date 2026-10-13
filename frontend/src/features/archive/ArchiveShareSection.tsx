import { useState } from "react"
import { CheckCircle2, Copy, Eye, EyeOff, FolderOpen, Play, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminFeedback, AdminPanel, AdminStatus, AdminToggle } from "@/features/cockpit/admin/ui"
import type { ArchiveShare } from "./api"
import { uncPath } from "./format"

interface Props {
  share: ArchiveShare
  host: string
  busy: boolean
  onSetupSamba: () => void
  onSwitch: (enabled: boolean) => void
}

function CopyButton({ value, label }: { value: string; label: string }) {
  const { t } = useTranslation("archive")
  const [copied, setCopied] = useState(false)
  async function copy() {
    await navigator.clipboard.writeText(value)
    setCopied(true); setTimeout(() => setCopied(false), 1500)
  }
  return (
    <AdminAction tone="ghost" className="px-2" onClick={copy} aria-label={label} title={copied ? t("share.copied") : label}>
      {copied ? <CheckCircle2 size={11} className="text-emerald-400" /> : <Copy size={11} />}
    </AdminAction>
  )
}

function Login({ share, host }: { share: ArchiveShare; host: string }) {
  const { t } = useTranslation("archive")
  const [showPwd, setShowPwd] = useState(false)
  const unc = uncPath(host, share.name)
  return (
    <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 text-xs">
      <span className="text-[#8d9ab0]">{t("share.address")}</span>
      <span className="flex min-w-0 items-center gap-1.5">
        <span className="min-w-0 flex-1 truncate font-mono text-[#e8eef8]">{unc}</span>
        <CopyButton value={unc} label={t("share.copy_address")} />
      </span>
      <span className="text-[#8d9ab0]">{t("share.login")}</span>
      <span className="font-mono text-[#e8eef8]">{share.login}</span>
      <span className="text-[#8d9ab0]">{t("share.password")}</span>
      <span className="flex min-w-0 items-center gap-1.5">
        <span className="min-w-0 flex-1 truncate font-mono text-[#e8eef8]">
          {showPwd ? share.password : "••••••••••••"}
        </span>
        <AdminAction tone="ghost" className="px-2" onClick={() => setShowPwd(!showPwd)}
          aria-label={t("share.password")} title={t("share.password")}>
          {showPwd ? <EyeOff size={11} /> : <Eye size={11} />}
        </AdminAction>
        {share.password && <CopyButton value={share.password} label={t("share.copy_password")} />}
      </span>
    </div>
  )
}

/** Samba-Freigabe des System-Archivs: lesen + schreiben, Papierkorb. HydraHive legt sie selbst an, Schalter hier. */
export function ArchiveShareSection({ share, host, busy, onSetupSamba, onSwitch }: Props) {
  const { t } = useTranslation("archive")
  const active = share.enabled && share.samba_installed && share.samba_running
  return (
    <div data-archive-section="share">
      <AdminPanel
        title={t("share.title")}
        description={t("share.subtitle")}
        icon={FolderOpen}
        actions={(
          <AdminStatus tone={active ? "success" : "warning"} icon={active ? CheckCircle2 : XCircle}>
            {active ? t("share.active") : t("share.inactive")}
          </AdminStatus>
        )}
        bodyClassName="space-y-3"
      >
        {!share.samba_installed ? (
          <div className="space-y-2">
            <AdminFeedback tone="warning">{t("share.no_samba")}</AdminFeedback>
            <AdminAction tone="primary" data-archive-action="setup-samba" onClick={onSetupSamba}>
              <Play size={11} /> {t("share.setup_samba")}
            </AdminAction>
          </div>
        ) : (
          <>
            <AdminToggle
              label={t("share.switch")}
              checked={share.wanted}
              disabled={busy}
              data-archive-action="share-switch"
              onChange={(e) => onSwitch(e.target.checked)}
            />
            {share.paused_for_move && <AdminFeedback tone="warning">{t("share.paused_for_move")}</AdminFeedback>}
            {!share.wanted && <AdminFeedback>{t("share.switched_off")}</AdminFeedback>}
            {share.wanted && !share.enabled && <AdminFeedback tone="warning">{t("share.not_enabled")}</AdminFeedback>}
            {share.wanted && share.enabled && <Login share={share} host={host} />}
          </>
        )}
        <p className="text-[11px] leading-relaxed text-[#8d9ab0]">{t("share.hint")}</p>
      </AdminPanel>
    </div>
  )
}
