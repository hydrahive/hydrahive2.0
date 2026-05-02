import { useEffect, useState } from "react"
import { Network, WifiOff } from "lucide-react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"
import type { TailscaleStatus } from "./_tailscaleTypes"
import { TailscaleConnectedView } from "./_TailscaleConnectedView"
import { TailscaleLoginForm } from "./_TailscaleLoginForm"

const REFRESH_MS = 15_000

export function TailscaleCard() {
  const { t } = useTranslation("system")
  const [status, setStatus] = useState<TailscaleStatus | null>(null)
  const [showLogin, setShowLogin] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    try {
      setStatus(await api.get<TailscaleStatus>("/tailscale/status"))
    } catch { /* leise */ }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, REFRESH_MS)
    return () => clearInterval(id)
  }, [])

  async function handleConnect(key: string) {
    setConnecting(true); setError(null)
    try {
      const s = await api.post<TailscaleStatus>("/tailscale/up", { authkey: key })
      setStatus(s); setShowLogin(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : t("tailscale.error_connect"))
    } finally { setConnecting(false) }
  }

  async function handleLogout() {
    setLoggingOut(true); setError(null)
    try {
      setStatus(await api.post<TailscaleStatus>("/tailscale/logout", {}))
    } catch (e) {
      setError(e instanceof Error ? e.message : t("tailscale.error_logout"))
    } finally { setLoggingOut(false) }
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
        <TailscaleConnectedView status={status} loggingOut={loggingOut} onLogout={handleLogout} />
      )}

      {error && !showLogin && <p className="text-xs text-rose-400">{error}</p>}

      {!connected && !showLogin && (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <button onClick={() => setShowLogin(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 text-xs font-medium hover:bg-emerald-500/20 transition-colors">
            <Network size={12} /> {t("tailscale.connect")}
          </button>
        </div>
      )}

      {showLogin && !connected && (
        <TailscaleLoginForm
          connecting={connecting}
          error={error}
          onConnect={handleConnect}
          onCancel={() => { setShowLogin(false); setError(null) }}
        />
      )}
    </div>
  )
}
