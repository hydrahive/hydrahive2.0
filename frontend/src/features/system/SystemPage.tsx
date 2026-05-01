import { useEffect, useState } from "react"
import {
  Activity, Bot, Database, Folder, MessageSquare, Mic, RotateCw, Server, Wrench, Zap,
} from "lucide-react"
import { useTranslation } from "react-i18next"
import { HelpButton } from "@/i18n/HelpButton"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { RestartModal } from "@/shared/RestartModal"
import { useRestart } from "@/shared/useRestart"
import { systemApi, type HealthCheck, type SystemInfo, type SystemStats } from "./api"
import { AgentLinkCard } from "./AgentLinkCard"
import { BridgeCard } from "./BridgeCard"
import { TailscaleCard } from "./TailscaleCard"
import { BackupCard } from "./BackupCard"
import { HealthBar } from "./HealthBar"
import { StatCard } from "./StatCard"
import { VoiceInstallModal, type VoiceInstallState } from "./VoiceInstallModal"

const REFRESH_MS = 10_000

export function SystemPage() {
  const { t } = useTranslation("system")
  const { t: tAgents } = useTranslation("agents")
  const { t: tNav } = useTranslation("nav")
  const role = useAuthStore((s) => s.role)
  const restart = useRestart()
  const [voiceState, setVoiceState] = useState<"idle" | VoiceInstallState>("idle")
  const [voiceError, setVoiceError] = useState<string | null>(null)
  const [info, setInfo] = useState<SystemInfo | null>(null)
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [checks, setChecks] = useState<HealthCheck[]>([])

  async function loadAll() {
    try {
      const [i, s, h] = await Promise.all([
        systemApi.info(), systemApi.stats(), systemApi.health(),
      ])
      setInfo(i); setStats(s); setChecks(h.checks)
    } catch { /* leise */ }
  }

  useEffect(() => {
    loadAll()
    const t = setInterval(loadAll, REFRESH_MS)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">{t("title")}</h1>
          <p className="text-zinc-500 text-sm mt-0.5">
            {info
              ? t("subtitle_with_uptime", { seconds: REFRESH_MS / 1000, uptime: formatUptime(info.uptime_seconds, t) })
              : t("subtitle", { seconds: REFRESH_MS / 1000 })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {role === "admin" && (
            <>
              <button
                onClick={() => { setVoiceState("confirm"); setVoiceError(null) }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-emerald-200 text-xs font-medium hover:bg-emerald-500/20 transition-colors"
              >
                <Mic size={12} />
                Voice installieren
              </button>
              <button
                onClick={restart.open}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/25 text-rose-200 text-xs font-medium hover:bg-rose-500/20 transition-colors"
              >
                <RotateCw size={12} />
                {tNav("restart.button")}
              </button>
            </>
          )}
          <HelpButton topic="system" />
        </div>
      </div>

      {restart.state !== "idle" && (
        <RestartModal
          state={restart.state}
          errorMessage={restart.error}
          onConfirm={restart.confirm}
          onClose={restart.close}
        />
      )}

      {voiceState !== "idle" && (
        <VoiceInstallModal
          state={voiceState}
          errorMessage={voiceError}
          onConfirm={async () => {
            setVoiceState("starting")
            setVoiceError(null)
            try {
              await systemApi.installVoice()
              setVoiceState("running")
              // Poll log until "bereit" appears or 5 minutes pass
              const startedAt = Date.now()
              while (Date.now() - startedAt < 300_000) {
                await new Promise((r) => setTimeout(r, 3000))
                try {
                  const log = await systemApi.voiceLog(50)
                  const text = log.lines.join("")
                  if (text.includes("Voice Interface bereit")) {
                    setVoiceState("done")
                    return
                  }
                } catch { /* ignore */ }
              }
              setVoiceState("done")
            } catch (e) {
              setVoiceState("failed")
              setVoiceError(e instanceof Error ? e.message : String(e))
            }
          }}
          onClose={() => setVoiceState("idle")}
        />
      )}

      <HealthBar checks={checks} />

      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Bot} label={t("stats.agents")} value={stats.agents.total}
            detail={Object.entries(stats.agents.by_type)
              .map(([k, v]) => t("stats.agents_detail", { count: v, type: tAgents(`type.${k}`) }))
              .join(", ")}
            glow="bg-violet-500/40" />
          <StatCard icon={Folder} label={t("stats.projects")} value={stats.projects.total}
            detail={t("stats.projects_detail", { count: stats.projects.active })} glow="bg-indigo-500/40" />
          <StatCard icon={MessageSquare} label={t("stats.sessions")} value={stats.sessions.total}
            detail={t("stats.sessions_detail", { count: stats.sessions.active })} glow="bg-fuchsia-500/40" />
          <StatCard icon={Activity} label={t("stats.messages")} value={stats.messages.total}
            detail={t("stats.messages_detail", { count: stats.messages.compactions })} glow="bg-amber-500/40" />
          <StatCard icon={Wrench} label={t("stats.tool_calls")} value={stats.tool_calls.total}
            detail={t("stats.tool_calls_detail", { rate: stats.tool_calls.success_rate })} glow="bg-emerald-500/40" />
          <StatCard icon={Database} label={t("stats.db_size")}
            value={info ? formatBytes(info.db_size_bytes) : "—"}
            detail={t("stats.db_size_detail")} glow="bg-cyan-500/40" />
          <StatCard icon={Zap} label={t("stats.python")} value={info?.python ?? "—"}
            detail={info?.platform} glow="bg-yellow-500/40" />
          <StatCard icon={Server} label={t("stats.version")} value={info?.version ?? "—"}
            detail={t("stats.version_detail")} glow="bg-rose-500/40" />
        </div>
      )}

      {info && (
        <div className="rounded-xl border border-white/[6%] bg-white/[2%] p-4 space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500 mb-2">{t("paths.title")}</p>
          <PathRow label={t("paths.data")} value={info.data_dir} />
          <PathRow label={t("paths.config")} value={info.config_dir} />
          <PathRow label={t("paths.db")} value={info.db_path} />
        </div>
      )}

      <AgentLinkCard />
      {role === "admin" && <TailscaleCard />}
      {role === "admin" && <BridgeCard />}

      {role === "admin" && <BackupCard />}
    </div>
  )
}

function PathRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline gap-3 text-xs">
      <span className="w-16 text-zinc-500 flex-shrink-0">{label}</span>
      <span className="text-zinc-300 font-mono truncate">{value}</span>
    </div>
  )
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 ** 3) return `${(n / 1024 / 1024).toFixed(1)} MB`
  return `${(n / 1024 ** 3).toFixed(2)} GB`
}

function formatUptime(seconds: number, t: (key: string, opts?: Record<string, unknown>) => string): string {
  if (seconds < 60) return t("uptime.seconds", { n: Math.floor(seconds) })
  if (seconds < 3600) return t("uptime.minutes", { m: Math.floor(seconds / 60), s: Math.floor(seconds % 60) })
  if (seconds < 86400) return t("uptime.hours", { h: Math.floor(seconds / 3600), m: Math.floor((seconds % 3600) / 60) })
  return t("uptime.days", { d: Math.floor(seconds / 86400), h: Math.floor((seconds % 86400) / 3600) })
}
