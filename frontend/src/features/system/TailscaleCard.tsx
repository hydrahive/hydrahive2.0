import { useEffect, useState } from "react"
import { Download, Network, WifiOff } from "lucide-react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"
import {
  AdminAction,
  AdminCodeBlock,
  AdminFeedback,
  AdminPanel,
  AdminStatus,
} from "@/features/cockpit/admin/ui"
import type { TailscaleStatus } from "./_tailscaleTypes"
import { TailscaleConnectedView } from "./_TailscaleConnectedView"
import { TailscaleInviteSection } from "./_TailscaleInviteSection"
import { TailscaleLoginForm } from "./_TailscaleLoginForm"

const REFRESH_MS = 15_000

interface InstallResult {
  ok: boolean
  rc: number
  output: string
  status: TailscaleStatus
}

export function TailscaleCard() {
  const { t } = useTranslation("system")
  const [status, setStatus] = useState<TailscaleStatus | null>(null)
  const [showLogin, setShowLogin] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const [installing, setInstalling] = useState(false)
  const [installOutput, setInstallOutput] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    try {
      setStatus(await api.get<TailscaleStatus>("/tailscale/status"))
    } catch { /* leise */ }
  }

  useEffect(() => {
    async function tick() { await load() }
    tick()
    const id = setInterval(tick, REFRESH_MS)
    return () => clearInterval(id)
  }, [])

  async function handleInstall() {
    setInstalling(true); setError(null); setInstallOutput(null)
    try {
      const r = await api.post<InstallResult>("/tailscale/install", {})
      setStatus(r.status)
      if (!r.ok) {
        setError(t("tailscale.install_failed"))
        setInstallOutput(r.output)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : t("tailscale.install_failed"))
    } finally { setInstalling(false) }
  }

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
      <AdminPanel
        title={t("tailscale.title")}
        description={t("tailscale.not_installed")}
        icon={WifiOff}
        bodyClassName="space-y-3"
      >
        <p className="text-xs text-[#8d9ab0]">{t("tailscale.install_hint")}</p>
        <AdminAction onClick={handleInstall} disabled={installing} tone="primary">
          <Download size={12} className={installing ? "animate-pulse" : ""} />
          {installing ? t("tailscale.installing") : t("tailscale.install_button")}
        </AdminAction>
        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
        {installOutput && <AdminCodeBlock className="max-h-40">{installOutput}</AdminCodeBlock>}
      </AdminPanel>
    )
  }

  const connected = status.connected
  const Icon = connected ? Network : WifiOff

  return (
    <AdminPanel
      title={t("tailscale.title")}
      icon={Icon}
      actions={(
        <AdminStatus tone={connected ? "success" : "danger"} dot>
          {connected ? t("tailscale.connected") : t("tailscale.disconnected")}
        </AdminStatus>
      )}
      bodyClassName="space-y-3"
    >
      {connected && (
        <>
          <TailscaleConnectedView status={status} loggingOut={loggingOut} onLogout={handleLogout} />
          <TailscaleInviteSection />
        </>
      )}

      {error && !showLogin && <AdminFeedback tone="danger">{error}</AdminFeedback>}

      {!connected && !showLogin && (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <AdminAction onClick={() => setShowLogin(true)} tone="primary">
            <Network size={12} /> {t("tailscale.connect")}
          </AdminAction>
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
    </AdminPanel>
  )
}
