import { useEffect, useState } from "react"
import {
  Activity, Bot, Database, Folder, MessageSquare, Server, Wrench, Zap,
} from "lucide-react"
import { systemApi, type HealthCheck, type SystemInfo, type SystemStats } from "./api"
import { HealthBar } from "./HealthBar"
import { StatCard } from "./StatCard"

const REFRESH_MS = 10_000

export function SystemPage() {
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
      <div>
        <h1 className="text-xl font-bold text-white">System-Status</h1>
        <p className="text-zinc-500 text-sm mt-0.5">
          Auto-Refresh alle {REFRESH_MS / 1000}s · {info && `läuft seit ${formatUptime(info.uptime_seconds)}`}
        </p>
      </div>

      <HealthBar checks={checks} />

      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Bot} label="Agents" value={stats.agents.total}
            detail={Object.entries(stats.agents.by_type).map(([k, v]) => `${v} ${k}`).join(", ")}
            glow="bg-violet-500/40" />
          <StatCard icon={Folder} label="Projekte" value={stats.projects.total}
            detail={`${stats.projects.active} aktiv`} glow="bg-indigo-500/40" />
          <StatCard icon={MessageSquare} label="Sessions" value={stats.sessions.total}
            detail={`${stats.sessions.active} aktiv`} glow="bg-fuchsia-500/40" />
          <StatCard icon={Activity} label="Messages" value={stats.messages.total}
            detail={`${stats.messages.compactions} Compactions`} glow="bg-amber-500/40" />
          <StatCard icon={Wrench} label="Tool-Calls" value={stats.tool_calls.total}
            detail={`${stats.tool_calls.success_rate}% Success`} glow="bg-emerald-500/40" />
          <StatCard icon={Database} label="DB-Größe"
            value={info ? formatBytes(info.db_size_bytes) : "—"}
            detail="sessions.db" glow="bg-cyan-500/40" />
          <StatCard icon={Zap} label="Python" value={info?.python ?? "—"}
            detail={info?.platform} glow="bg-yellow-500/40" />
          <StatCard icon={Server} label="Version" value={info?.version ?? "—"}
            detail="HydraHive" glow="bg-rose-500/40" />
        </div>
      )}

      {info && (
        <div className="rounded-xl border border-white/[6%] bg-white/[2%] p-4 space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500 mb-2">Pfade</p>
          <PathRow label="Data" value={info.data_dir} />
          <PathRow label="Config" value={info.config_dir} />
          <PathRow label="DB" value={info.db_path} />
        </div>
      )}
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

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
  return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`
}
