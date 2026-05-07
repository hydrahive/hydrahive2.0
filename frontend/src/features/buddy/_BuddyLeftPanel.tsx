import { useEffect, useState } from "react"
import { Activity, Loader2 } from "lucide-react"
import { dashboardApi, type DashboardSummary } from "@/features/dashboard/api"

function PanelBox({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900/90 to-zinc-950/90 shadow-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[6%] bg-black/20 flex items-center gap-2">
        {icon}
        <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">{title}</span>
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}

function StatRow({ label, value, accent }: { label: string; value: React.ReactNode; accent?: string }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-white/[4%] last:border-0">
      <span className="text-xs text-zinc-500">{label}</span>
      <span className={`text-xs font-mono font-medium ${accent ?? "text-zinc-300"}`}>{value}</span>
    </div>
  )
}

export function BuddyLeftPanel() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)

  useEffect(() => {
    dashboardApi.summary().then(setSummary).catch(() => {})
  }, [])

  return (
    <div className="flex flex-col gap-4 w-60">
      <PanelBox title="Zahnfee" icon={<span className="text-sm">🦷</span>}>
        <p className="text-xs text-zinc-500 italic leading-relaxed">
          Noch kein Briefing für heute.
        </p>
      </PanelBox>

      <PanelBox title="System" icon={<Activity size={13} className="text-zinc-400" />}>
        {!summary ? (
          <Loader2 size={14} className="text-zinc-600 animate-spin" />
        ) : (
          <div>
            <StatRow label="Tokens heute" value={summary.stats.tokens_today.toLocaleString("de")} />
            <StatRow label="Aktive Sessions" value={summary.stats.active_sessions} />
            <StatRow label="Tool Calls" value={summary.stats.tool_calls_today} />
            <StatRow
              label="Server"
              value={`${summary.stats.servers_running} / ${summary.stats.servers_total}`}
              accent={summary.stats.servers_running > 0 ? "text-emerald-400" : "text-zinc-500"}
            />
            <StatRow
              label="Backend"
              value={summary.health.backend.ok ? "✓ OK" : "✗ Fehler"}
              accent={summary.health.backend.ok ? "text-emerald-400" : "text-rose-400"}
            />
          </div>
        )}
      </PanelBox>
    </div>
  )
}
