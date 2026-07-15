import { useEffect, useState } from "react"
import { ExternalLink, Link2, Link2Off, Loader2, RefreshCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import {
  AdminAction,
  AdminFeedback,
  AdminPanel,
  AdminStatus,
  adminActionClass,
} from "@/features/cockpit/admin/ui"
import { relTime, type AgentLinkStatus } from "./_agentLinkHelpers"
import { AgentLinkKnownAgents } from "./_AgentLinkKnownAgents"

const REFRESH_MS = 10_000

export function AgentLinkCard() {
  const { t, i18n } = useTranslation("system")
  const { t: tCommon } = useTranslation("common")
  const role = useAuthStore((s) => s.role)
  const [status, setStatus] = useState<AgentLinkStatus | null>(null)
  const [reconnecting, setReconnecting] = useState(false)
  const [reconnectError, setReconnectError] = useState<string | null>(null)

  async function load() {
    try { setStatus(await api.get<AgentLinkStatus>("/agentlink/status")) }
    catch { /* leise */ }
  }

  useEffect(() => {
    let alive = true
    async function tick() { if (alive) await load() }
    tick()
    const id = setInterval(tick, REFRESH_MS)
    return () => { alive = false; clearInterval(id) }
  }, [])

  async function reconnect() {
    setReconnecting(true); setReconnectError(null)
    try {
      await api.post("/agentlink/reconnect", {})
      await new Promise((r) => setTimeout(r, 1500))
      await load()
    } catch (e) {
      setReconnectError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setReconnecting(false) }
  }

  if (!status) return null
  if (!status.configured) {
    return (
      <AdminPanel
        title={t("agentlink.title")}
        description={t("agentlink.not_configured")}
        icon={Link2Off}
      >
        <p className="text-xs leading-relaxed text-[#8d9ab0]">{t("agentlink.not_configured_hint")}</p>
      </AdminPanel>
    )
  }

  const Icon = status.connected ? Link2 : Link2Off

  return (
    <AdminPanel
      title={t("agentlink.title")}
      icon={Icon}
      actions={(
        <AdminStatus tone={status.connected ? "success" : "danger"} dot>
          {status.connected ? t("agentlink.connected") : t("agentlink.disconnected")}
        </AdminStatus>
      )}
      bodyClassName="space-y-3"
    >
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <span className="text-[#8d9ab0]">{t("agentlink.url")}</span>
        <span className="truncate font-mono text-[#e8eef8]">{status.url ?? "—"}</span>
        <span className="text-[#8d9ab0]">{t("agentlink.ws")}</span>
        <span className={`truncate font-mono ${status.ws_connected ? "text-emerald-300" : "text-rose-300"}`}>
          {status.ws_url ?? "—"}
        </span>
        <span className="text-[#8d9ab0]">{t("agentlink.agent_id")}</span>
        <span className="font-mono text-[#e8eef8]">{status.agent_id ?? "—"}</span>
        <span className="text-[#8d9ab0]">{t("agentlink.timeout")}</span>
        <span className="font-mono text-[#e8eef8]">{status.handoff_timeout_s ?? "—"}s</span>
        {status.last_connect_at && <>
          <span className="text-[#8d9ab0]">{t("agentlink.last_connect")}</span>
          <span className="font-mono text-[#8d9ab0]" title={status.last_connect_at}>
            vor {relTime(status.last_connect_at, i18n.language)}
          </span>
        </>}
        {(status.reconnect_attempts ?? 0) > 0 && <>
          <span className="text-[#8d9ab0]">{t("agentlink.reconnects")}</span>
          <span className={`font-mono ${(status.reconnect_attempts ?? 0) > 5 ? "text-amber-300" : "text-[#8d9ab0]"}`}>
            {status.reconnect_attempts}
          </span>
        </>}
        {(status.pending_handoffs ?? 0) > 0 && <>
          <span className="text-[#8d9ab0]">{t("agentlink.pending")}</span>
          <span className="font-mono text-amber-300">{status.pending_handoffs}</span>
        </>}
      </div>

      {status.known_agents && status.known_agents.length > 0 && (
        <AgentLinkKnownAgents agents={status.known_agents} locale={i18n.language} />
      )}

      {!status.connected && status.last_error && (
        <AdminFeedback tone="danger" className="font-mono break-all">{status.last_error}</AdminFeedback>
      )}

      {reconnectError && <AdminFeedback tone="danger">{reconnectError}</AdminFeedback>}

      <div className="flex flex-wrap gap-2">
        {role === "admin" && !status.connected && (
          <AdminAction onClick={reconnect} disabled={reconnecting} tone="primary">
            {reconnecting ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
            {t("agentlink.reconnect")}
          </AdminAction>
        )}
        {status.dashboard_url && (
          <a
            href={status.dashboard_url}
            target="_blank"
            rel="noreferrer"
            className={adminActionClass("default")}
          >
            <ExternalLink size={12} />
            {t("agentlink.open_dashboard")}
          </a>
        )}
      </div>
    </AdminPanel>
  )
}
