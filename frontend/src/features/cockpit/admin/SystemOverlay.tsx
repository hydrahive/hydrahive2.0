import { useEffect, useState } from "react"
import { Activity, Bot, Database, Folder, MessageSquare, Mic, RotateCw, Server, SlidersHorizontal, Wrench, Zap } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { RestartModal } from "@/shared/RestartModal"
import { useRestart } from "@/shared/useRestart"
import { systemApi, type HealthCheck, type SystemInfo, type SystemStats } from "@/features/system/api"
import { AgentLinkCard } from "@/features/system/AgentLinkCard"
import { BridgeCard } from "@/features/system/BridgeCard"
import { SambaCard } from "@/features/system/SambaCard"
import { TailscaleCard } from "@/features/system/TailscaleCard"
import { BackupCard } from "@/features/system/BackupCard"
import { MigrationCard } from "@/features/system/MigrationCard"
import { HealthBar } from "@/features/system/HealthBar"
import { StatCard } from "@/features/system/StatCard"
import { VoiceInstallModal } from "@/features/system/VoiceInstallModal"
import { useVoiceInstall } from "@/features/system/useVoiceInstall"
import { PathRow, formatBytes, formatUptime } from "@/features/system/_systemHelpers"
import { CockpitButton } from "../CockpitButton"
import { AdminOverlay } from "./AdminOverlay"

const REFRESH_MS = 10_000

export function SystemOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("system")
  const { t: tAgents } = useTranslation("agents")
  const { t: tNav } = useTranslation("nav")
  const role = useAuthStore((s) => s.role)
  const restart = useRestart()
  const voice = useVoiceInstall()
  const [info, setInfo] = useState<SystemInfo | null>(null)
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [checks, setChecks] = useState<HealthCheck[]>([])

  async function loadAll() {
    try {
      const [i, s, h] = await Promise.all([systemApi.info(), systemApi.stats(), systemApi.health()])
      setInfo(i); setStats(s); setChecks(h.checks)
    } catch { /* leise */ }
  }
  useEffect(() => {
    loadAll()
    const id = setInterval(loadAll, REFRESH_MS)
    return () => clearInterval(id)
  }, [])

  return (
    <AdminOverlay
      eyebrow="Admin"
      title={t("title")}
      onClose={onClose}
      maxWidthClass="max-w-6xl"
      headerActions={role === "admin" ? (
        <div className="flex items-center gap-2">
          <CockpitButton onClick={() => window.open("/system/settings", "_self")}>
            <SlidersHorizontal size={12} className="mr-1 inline" />Einstellungen
          </CockpitButton>
          <CockpitButton onClick={voice.begin}>
            <Mic size={12} className="mr-1 inline" />Voice installieren
          </CockpitButton>
          <CockpitButton onClick={restart.open}>
            <RotateCw size={12} className="mr-1 inline" />{tNav("restart.button")}
          </CockpitButton>
        </div>
      ) : undefined}
    >
      <div className="space-y-6">
        <p className="text-sm text-[#8d9ab0]">
          {info
            ? t("subtitle_with_uptime", { seconds: REFRESH_MS / 1000, uptime: formatUptime(info.uptime_seconds, t) })
            : t("subtitle", { seconds: REFRESH_MS / 1000 })}
        </p>

        <HealthBar checks={checks} />

        {stats && (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard icon={Bot} label={t("stats.agents")} value={stats.agents.total}
              detail={Object.entries(stats.agents.by_type).map(([k, v]) => t("stats.agents_detail", { count: v, type: tAgents(`type.${k}`) })).join(", ")} glow="bg-violet-500/40" />
            <StatCard icon={Folder} label={t("stats.projects")} value={stats.projects.total}
              detail={t("stats.projects_detail", { count: stats.projects.active })} glow="bg-indigo-500/40" />
            <StatCard icon={MessageSquare} label={t("stats.sessions")} value={stats.sessions.total}
              detail={t("stats.sessions_detail", { count: stats.sessions.active })} glow="bg-fuchsia-500/40" />
            <StatCard icon={Activity} label={t("stats.messages")} value={stats.messages.total}
              detail={t("stats.messages_detail", { count: stats.messages.compactions })} glow="bg-amber-500/40" />
            <StatCard icon={Wrench} label={t("stats.tool_calls")} value={stats.tool_calls.total}
              detail={t("stats.tool_calls_detail", { rate: stats.tool_calls.success_rate })} glow="bg-emerald-500/40" />
            <StatCard icon={Database} label={t("stats.db_size")} value={info ? formatBytes(info.db_size_bytes) : "—"}
              detail={t("stats.db_size_detail")} glow="bg-cyan-500/40" />
            <StatCard icon={Zap} label={t("stats.python")} value={info?.python ?? "—"} detail={info?.platform} glow="bg-yellow-500/40" />
            <StatCard icon={Server} label={t("stats.version")} value={info?.version ?? "—"}
              detail={t("stats.version_detail")} glow="bg-rose-500/40" />
          </div>
        )}

        {info && (
          <div className="space-y-1 rounded-[6px] border border-[#2a364b] bg-[#111827] p-4">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[#8d9ab0]">{t("paths.title")}</p>
            <PathRow label={t("paths.data")} value={info.data_dir} />
            <PathRow label={t("paths.config")} value={info.config_dir} />
            <PathRow label={t("paths.db")} value={info.db_path} />
          </div>
        )}

        <AgentLinkCard />
        {role === "admin" && <TailscaleCard />}
        {role === "admin" && <BridgeCard />}
        {role === "admin" && <SambaCard />}
        {role === "admin" && <BackupCard />}
        {role === "admin" && <MigrationCard />}
      </div>

      {restart.state !== "idle" && (
        <RestartModal state={restart.state} errorMessage={restart.error} onConfirm={restart.confirm} onClose={restart.close} />
      )}
      {voice.state !== "idle" && (
        <VoiceInstallModal state={voice.state} errorMessage={voice.error} onConfirm={voice.confirm} onClose={voice.close} />
      )}
    </AdminOverlay>
  )
}
