import { Check, ClipboardCopy, ExternalLink, LogOut } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
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
        <span className="text-zinc-500">IP</span>
        <span className="text-emerald-300 font-mono">{status.ip ?? "—"}</span>
        <span className="text-zinc-500">{t("tailscale.hostname")}</span>
        <span className="text-zinc-300 font-mono">{status.hostname ?? "—"}</span>
        <span className="text-zinc-500">{t("tailscale.dns")}</span>
        <span className="text-zinc-300 font-mono truncate">{status.dns_name ?? "—"}</span>
        {status.tailnet && <>
          <span className="text-zinc-500">Tailnet</span>
          <span className="text-zinc-300 font-mono">{status.tailnet}</span>
        </>}
        {status.version && <>
          <span className="text-zinc-500">{t("tailscale.version")}</span>
          <span className="text-zinc-500 font-mono text-[11px]">{status.version}</span>
        </>}
        {status.exit_node_active && <>
          <span className="text-zinc-500">{t("tailscale.exit_node")}</span>
          <span className="text-amber-300 font-mono">→ {status.exit_node_active}</span>
        </>}
      </div>

      {status.peers && status.peers.length > 0 && (
        <div className="pt-1 border-t border-white/[6%]">
          <p className="text-[10.5px] uppercase tracking-wider text-zinc-500 mb-1.5">
            {t("tailscale.peers", { count: status.peers.length })}
          </p>
          <div className="space-y-1">
            {status.peers.map((p) => (
              <div key={p.dns_name || p.hostname} className="flex items-center gap-2 text-[11px]">
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${p.online ? "bg-emerald-400" : "bg-zinc-600"}`} />
                <span className={`font-mono truncate flex-1 min-w-0 ${p.online ? "text-zinc-200" : "text-zinc-500"}`}>
                  {p.hostname}
                </span>
                <span className="text-zinc-500 font-mono">{p.ip ?? "—"}</span>
                {p.exit_node && (
                  <span className="px-1 rounded bg-amber-500/15 border border-amber-500/30 text-[9px] text-amber-300">EXIT</span>
                )}
                {p.exit_node_option && !p.exit_node && (
                  <span className="px-1 rounded bg-zinc-500/15 border border-zinc-500/30 text-[9px] text-zinc-500">exit?</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 pt-1">
        <button onClick={copyIp}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[4%] border border-white/[8%] text-zinc-300 text-xs hover:bg-white/[7%] transition-colors">
          {copied ? <Check size={12} className="text-emerald-400" /> : <ClipboardCopy size={12} />}
          {copied ? t("tailscale.copied") : t("tailscale.copy_ip")}
        </button>
        <a href={ADMIN_URL} target="_blank" rel="noreferrer"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[4%] border border-white/[8%] text-zinc-300 text-xs hover:bg-white/[7%] transition-colors">
          <ExternalLink size={12} /> {t("tailscale.admin_console")}
        </a>
        <button onClick={onLogout} disabled={loggingOut}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs hover:bg-rose-500/20 transition-colors disabled:opacity-40">
          <LogOut size={12} /> {t("tailscale.logout")}
        </button>
      </div>
    </>
  )
}
