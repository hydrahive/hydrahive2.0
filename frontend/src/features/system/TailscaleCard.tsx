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
import { addonOutcome, addonsApi, lastRun } from "./addonsApi"
import { TailscaleConnectedView } from "./_TailscaleConnectedView"
import { TailscaleInviteSection } from "./_TailscaleInviteSection"
import { TailscaleLoginForm } from "./_TailscaleLoginForm"
import { TailscaleBrowserLogin } from "./_TailscaleBrowserLogin"

const REFRESH_MS = 15_000

const INSTALL_POLL_MS = 2000
const INSTALL_MAX_MS = 10 * 60 * 1000

export function TailscaleCard() {
  const { t } = useTranslation("system")
  const [status, setStatus] = useState<TailscaleStatus | null>(null)
  const [showLogin, setShowLogin] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const [installing, setInstalling] = useState(false)
  const [installOutput, setInstallOutput] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loginUrl, setLoginUrl] = useState<string | null>(null)
  const [loginBusy, setLoginBusy] = useState(false)
  const [loginError, setLoginError] = useState<string | null>(null)

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

  // Installation läuft über den Zusatz-Module-Runner (installer/addon-ctl.sh); hier nur anstoßen und mitlesen.
  async function handleInstall() {
    setInstalling(true); setError(null); setInstallOutput(null)
    try {
      await addonsApi.install("tailscale")
      const startedAt = Date.now()
      while (Date.now() - startedAt < INSTALL_MAX_MS) {
        await new Promise((resolve) => setTimeout(resolve, INSTALL_POLL_MS))
        const r = await addonsApi.log(60).catch(() => null)
        const lines = lastRun(r?.lines ?? [])
        setInstallOutput(lines.join(""))
        const outcome = addonOutcome(lines, "tailscale")
        if (outcome === "failed") { setError(t("tailscale.install_failed")); return }
        if (outcome === "ok") { await load(); return }
      }
      setError(t("tailscale.install_failed"))
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

  // Anmeldung ohne Auth-Key: Link von tailscale.com holen; die Karte prüft danach alle 15 s den Status.
  async function handleBrowserLogin() {
    setLoginBusy(true); setLoginError(null)
    try {
      const r = await api.post<{ auth_url: string | null }>("/tailscale/login", {})
      setLoginUrl(r.auth_url)
      if (!r.auth_url) await load()
    } catch (e) {
      setLoginError(e instanceof Error ? e.message : t("tailscale.error_connect"))
    } finally { setLoginBusy(false) }
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
        <p className="text-xs text-[#9aa7bc]">{t("tailscale.install_hint")}</p>
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
        <TailscaleBrowserLogin url={loginUrl ?? status.auth_url ?? null} busy={loginBusy} error={loginError}
          onStart={handleBrowserLogin} />
      )}

      {!connected && !showLogin && (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <AdminAction onClick={() => setShowLogin(true)} tone="primary">
            <Network size={12} /> {t("tailscale.connect_authkey")}
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
