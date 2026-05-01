import { useEffect, useRef, useState } from "react"
import { Check, ClipboardCopy, ExternalLink, LogOut, Network, WifiOff } from "lucide-react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"

interface TailscaleStatus {
  installed: boolean
  connected: boolean
  backend_state?: string
  ip?: string
  hostname?: string
  dns_name?: string
  tailnet?: string
  auth_url?: string
  error?: string
}

const REFRESH_MS = 15_000
const ADMIN_URL = "https://login.tailscale.com/admin/settings/keys"

export function TailscaleCard() {
  const { t } = useTranslation("system")
  const [status, setStatus] = useState<TailscaleStatus | null>(null)
  const [showLogin, setShowLogin] = useState(false)
  const [authkey, setAuthkey] = useState("")
  const [connecting, setConnecting] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  async function load() {
    try {
      const s = await api.get<TailscaleStatus>("/tailscale/status")
      setStatus(s)
    } catch { /* leise */ }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, REFRESH_MS)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (showLogin) setTimeout(() => inputRef.current?.focus(), 50)
  }, [showLogin])

  async function handleConnect() {
    if (!authkey.trim()) return
    setConnecting(true); setError(null)
    try {
      const s = await api.post<TailscaleStatus>("/tailscale/up", { authkey: authkey.trim() })
      setStatus(s); setShowLogin(false); setAuthkey("")
    } catch (e) {
      setError(e instanceof Error ? e.message : t("tailscale.error_connect"))
    } finally { setConnecting(false) }
  }

  async function handleLogout() {
    setLoggingOut(true); setError(null)
    try {
      const s = await api.post<TailscaleStatus>("/tailscale/logout", {})
      setStatus(s)
    } catch (e) {
      setError(e instanceof Error ? e.message : t("tailscale.error_logout"))
    } finally { setLoggingOut(false) }
  }

  function copyIp() {
    if (!status?.ip) return
    navigator.clipboard.writeText(status.ip)
    setCopied(true); setTimeout(() => setCopied(false), 2000)
  }

  if (!status) return null

  if (!status.installed) {
    return (
      <div className="rounded-xl border border-white/[6%] bg-white/[2%] p-4 space-y-1">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">{t("tailscale.title")}</p>
        <p className="text-zinc-500 text-sm">{t("tailscale.not_installed")}</p>
      </div>
    )
  }

  const connected = status.connected
  const tone = connected ? "text-emerald-300" : "text-zinc-500"
  const dot = connected ? "bg-emerald-400" : "bg-zinc-600"
  const Icon = connected ? Network : WifiOff

  return (
    <div className="rounded-xl border border-white/[6%] bg-white/[2%] p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Icon size={14} className={tone} />
          <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">{t("tailscale.title")}</p>
        </div>
        <span className={`flex items-center gap-1.5 text-[11px] ${tone}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
          {connected ? t("tailscale.connected") : t("tailscale.disconnected")}
        </span>
      </div>

      {connected && (
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
        </div>
      )}

      {error && <p className="text-xs text-rose-400">{error}</p>}

      <div className="flex flex-wrap items-center gap-2 pt-1">
        {!connected && !showLogin && (
          <button onClick={() => setShowLogin(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 text-xs font-medium hover:bg-emerald-500/20 transition-colors">
            <Network size={12} /> {t("tailscale.connect")}
          </button>
        )}
        {connected && (
          <>
            <button onClick={copyIp}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[4%] border border-white/[8%] text-zinc-300 text-xs hover:bg-white/[7%] transition-colors">
              {copied ? <Check size={12} className="text-emerald-400" /> : <ClipboardCopy size={12} />}
              {copied ? t("tailscale.copied") : t("tailscale.copy_ip")}
            </button>
            <a href={ADMIN_URL} target="_blank" rel="noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[4%] border border-white/[8%] text-zinc-300 text-xs hover:bg-white/[7%] transition-colors">
              <ExternalLink size={12} /> {t("tailscale.admin_console")}
            </a>
            <button onClick={handleLogout} disabled={loggingOut}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs hover:bg-rose-500/20 transition-colors disabled:opacity-40">
              <LogOut size={12} /> {t("tailscale.logout")}
            </button>
          </>
        )}
      </div>

      {showLogin && !connected && (
        <div className="space-y-2 pt-1 border-t border-white/[6%]">
          <p className="text-[11px] text-zinc-500">{t("tailscale.authkey_hint")}{" "}
            <a href={ADMIN_URL} target="_blank" rel="noreferrer" className="text-violet-400 hover:underline">
              login.tailscale.com
            </a>
          </p>
          <div className="flex gap-2">
            <input ref={inputRef} type="password" value={authkey}
              onChange={(e) => setAuthkey(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleConnect()}
              placeholder={t("tailscale.authkey_placeholder")}
              className="flex-1 px-3 py-1.5 rounded-lg bg-zinc-900 border border-white/[8%] text-zinc-200 text-sm font-mono placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-emerald-500/40" />
            <button onClick={handleConnect} disabled={connecting || !authkey.trim()}
              className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium disabled:opacity-40 transition-colors">
              {connecting ? "…" : t("tailscale.connect")}
            </button>
            <button onClick={() => { setShowLogin(false); setError(null) }}
              className="px-3 py-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-white/5 text-sm transition-colors">
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
