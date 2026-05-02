import { useEffect, useState } from "react"
import { ExternalLink, Link2, Link2Off, Loader2, RefreshCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
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
      <div className="rounded-xl border border-white/[6%] bg-white/[2%] p-4 space-y-2">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
          {t("agentlink.title")}
        </p>
        <p className="text-zinc-300 text-sm">{t("agentlink.not_configured")}</p>
        <p className="text-[11px] text-zinc-500/70 leading-relaxed">{t("agentlink.not_configured_hint")}</p>
      </div>
    )
  }

  const Icon = status.connected ? Link2 : Link2Off
  const tone = status.connected ? "text-emerald-300" : "text-rose-300"
  const dot = status.connected ? "bg-emerald-400" : "bg-rose-400"

  return (
    <div className="rounded-xl border border-white/[6%] bg-white/[2%] p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Icon size={14} className={tone} />
          <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
            {t("agentlink.title")}
          </p>
        </div>
        <span className={`flex items-center gap-1.5 text-[11px] ${tone}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
          {status.connected ? t("agentlink.connected") : t("agentlink.disconnected")}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <span className="text-zinc-500">{t("agentlink.url")}</span>
        <span className="text-zinc-300 font-mono truncate">{status.url ?? "—"}</span>
        <span className="text-zinc-500">{t("agentlink.ws")}</span>
        <span className={`font-mono truncate ${status.ws_connected ? "text-emerald-300" : "text-zinc-500"}`}>
          {status.ws_url ?? "—"}
        </span>
        <span className="text-zinc-500">{t("agentlink.agent_id")}</span>
        <span className="text-zinc-300 font-mono">{status.agent_id ?? "—"}</span>
        <span className="text-zinc-500">{t("agentlink.timeout")}</span>
        <span className="text-zinc-300 font-mono">{status.handoff_timeout_s ?? "—"}s</span>
        {status.last_connect_at && <>
          <span className="text-zinc-500">{t("agentlink.last_connect")}</span>
          <span className="text-zinc-400 font-mono" title={status.last_connect_at}>
            vor {relTime(status.last_connect_at, i18n.language)}
          </span>
        </>}
        {(status.reconnect_attempts ?? 0) > 0 && <>
          <span className="text-zinc-500">{t("agentlink.reconnects")}</span>
          <span className={`font-mono ${(status.reconnect_attempts ?? 0) > 5 ? "text-amber-400" : "text-zinc-400"}`}>
            {status.reconnect_attempts}
          </span>
        </>}
        {(status.pending_handoffs ?? 0) > 0 && <>
          <span className="text-zinc-500">{t("agentlink.pending")}</span>
          <span className="text-amber-300 font-mono">{status.pending_handoffs}</span>
        </>}
      </div>

      {status.known_agents && status.known_agents.length > 0 && (
        <AgentLinkKnownAgents agents={status.known_agents} locale={i18n.language} />
      )}

      {!status.connected && status.last_error && (
        <p className="text-[11px] text-rose-300/80 bg-rose-500/[5%] border border-rose-500/15 rounded-md px-2 py-1 font-mono break-all">
          {status.last_error}
        </p>
      )}

      {reconnectError && (
        <p className="text-[11px] text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-md px-2 py-1">
          {reconnectError}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {role === "admin" && !status.connected && (
          <button onClick={reconnect} disabled={reconnecting}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-emerald-200 text-xs font-medium hover:bg-emerald-500/20 transition-colors disabled:opacity-40">
            {reconnecting ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
            {t("agentlink.reconnect")}
          </button>
        )}
        {status.dashboard_url && (
          <a href={status.dashboard_url} target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-500/10 border border-violet-500/25 text-violet-200 text-xs font-medium hover:bg-violet-500/20 transition-colors"
          >
            <ExternalLink size={12} />
            {t("agentlink.open_dashboard")}
          </a>
        )}
      </div>
    </div>
  )
}
