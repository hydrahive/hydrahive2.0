import { useEffect, useState } from "react"
import { ExternalLink, Link2, Link2Off } from "lucide-react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"

interface Status {
  configured: boolean
  connected: boolean
  ws_connected?: boolean
  url?: string
  ws_url?: string
  agent_id?: string
  handoff_timeout_s?: number
  known_agents?: string[]
  dashboard_url?: string
}

const REFRESH_MS = 10_000

export function AgentLinkCard() {
  const { t } = useTranslation("system")
  const [status, setStatus] = useState<Status | null>(null)

  useEffect(() => {
    let alive = true
    async function load() {
      try {
        const s = await api.get<Status>("/agentlink/status")
        if (alive) setStatus(s)
      } catch { /* leise */ }
    }
    load()
    const t = setInterval(load, REFRESH_MS)
    return () => { alive = false; clearInterval(t) }
  }, [])

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
      </div>

      {status.known_agents && status.known_agents.length > 0 && (
        <div className="pt-1 border-t border-white/[6%]">
          <p className="text-[10.5px] uppercase tracking-wider text-zinc-500 mb-1.5">
            {t("agentlink.known_agents", { count: status.known_agents.length })}
          </p>
          <div className="flex flex-wrap gap-1">
            {status.known_agents.map(a => (
              <span key={a} className="px-2 py-0.5 rounded bg-violet-500/10 border border-violet-500/20 text-[11px] text-violet-200 font-mono">
                {a}
              </span>
            ))}
          </div>
        </div>
      )}

      {status.dashboard_url && (
        <a href={status.dashboard_url} target="_blank" rel="noreferrer"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-500/10 border border-violet-500/25 text-violet-200 text-xs font-medium hover:bg-violet-500/20 transition-colors w-fit"
        >
          <ExternalLink size={12} />
          {t("agentlink.open_dashboard")}
        </a>
      )}
    </div>
  )
}
