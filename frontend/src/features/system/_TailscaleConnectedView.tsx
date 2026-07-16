import { Check, ClipboardCopy, ExternalLink, LogOut } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import {
  AdminAction,
  AdminStatus,
  adminActionClass,
} from "@/features/cockpit/admin/ui"
import type { TailscaleStatus } from "./_tailscaleTypes"

const ADMIN_URL = "https://login.tailscale.com/admin/settings/keys"

interface Props {
  status: TailscaleStatus
  loggingOut: boolean
  onLogout: () => void
}

export function TailscaleConnectedView({ status, loggingOut, onLogout }: Props) {
  const { t } = useTranslation("system")
  const [copied, setCopied] = useState(false)

  function copyIp() {
    if (!status.ip) return
    navigator.clipboard.writeText(status.ip)
    setCopied(true); setTimeout(() => setCopied(false), 2000)
  }

  return (
    <>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <span className="text-[#8d9ab0]">IP</span>
        <span className="font-mono text-[#e8eef8]">{status.ip ?? "—"}</span>
        <span className="text-[#8d9ab0]">{t("tailscale.hostname")}</span>
        <span className="font-mono text-[#e8eef8]">{status.hostname ?? "—"}</span>
        <span className="text-[#8d9ab0]">{t("tailscale.dns")}</span>
        <span className="truncate font-mono text-[#e8eef8]">{status.dns_name ?? "—"}</span>
        {status.tailnet && <>
          <span className="text-[#8d9ab0]">Tailnet</span>
          <span className="font-mono text-[#e8eef8]">{status.tailnet}</span>
        </>}
        {status.version && <>
          <span className="text-[#8d9ab0]">{t("tailscale.version")}</span>
          <span className="font-mono text-[11px] text-[#8d9ab0]">{status.version}</span>
        </>}
        {status.exit_node_active && <>
          <span className="text-[#8d9ab0]">{t("tailscale.exit_node")}</span>
          <span className="font-mono text-[#c8f2ff]">→ {status.exit_node_active}</span>
        </>}
      </div>

      {status.peers && status.peers.length > 0 && (
        <div className="border-t border-[#2a364b] pt-3">
          <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.12em] text-[#8d9ab0]">
            {t("tailscale.peers", { count: status.peers.length })}
          </p>
          <div className="space-y-1.5">
            {status.peers.map((p) => (
              <div key={p.dns_name || p.hostname} className="flex items-center gap-2 text-[11px]">
                <AdminStatus
                  tone={p.online ? "success" : "danger"}
                  dot
                  className="border-0 bg-transparent p-0"
                >
                  <span className="sr-only">{p.online ? "Online" : "Offline"}</span>
                </AdminStatus>
                <span className={`min-w-0 flex-1 truncate font-mono ${p.online ? "text-[#e8eef8]" : "text-[#8d9ab0]"}`}>
                  {p.hostname}
                </span>
                <span className="font-mono text-[#8d9ab0]">{p.ip ?? "—"}</span>
                {p.exit_node && <AdminStatus tone="neutral">EXIT</AdminStatus>}
                {p.exit_node_option && !p.exit_node && <AdminStatus tone="neutral">exit?</AdminStatus>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 pt-1">
        <AdminAction onClick={copyIp}>
          {copied ? <Check size={12} className="text-emerald-400" /> : <ClipboardCopy size={12} />}
          {copied ? t("tailscale.copied") : t("tailscale.copy_ip")}
        </AdminAction>
        <a href={ADMIN_URL} target="_blank" rel="noreferrer" className={adminActionClass("default")}>
          <ExternalLink size={12} /> {t("tailscale.admin_console")}
        </a>
        <AdminAction onClick={onLogout} disabled={loggingOut} tone="danger">
          <LogOut size={12} /> {t("tailscale.logout")}
        </AdminAction>
      </div>
    </>
  )
}
