import { useEffect, useState } from "react"
import { Activity, Loader2 } from "lucide-react"
import { dashboardApi, type DashboardSummary } from "@/features/dashboard/api"
import { zahnfeeApi, type Briefing } from "@/features/zahnfee/api"
import { Link } from "react-router-dom"

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

function ZahnfeeBox({ briefing }: { briefing: Briefing | null | undefined }) {
  if (briefing === undefined) {
    return (
      <PanelBox title="Zahnfee" icon={<span className="text-sm">🦷</span>}>
        <Loader2 size={14} className="text-zinc-600 animate-spin" />
      </PanelBox>
    )
  }
  if (!briefing) {
    return (
      <PanelBox title="Zahnfee" icon={<span className="text-sm">🦷</span>}>
        <p className="text-xs text-zinc-500 italic leading-relaxed">Noch kein Briefing für heute.</p>
        <Link to="/zahnfee" className="mt-2 block text-xs text-violet-400 hover:text-violet-300 transition-colors">Einrichten →</Link>
      </PanelBox>
    )
  }
  const sections = [
    { label: "Offen", value: briefing.open_items, color: "text-amber-400" },
    { label: "Gut", value: briefing.went_well, color: "text-emerald-400" },
    { label: "Schlecht", value: briefing.went_badly, color: "text-rose-400" },
    { label: "Heute", value: briefing.today, color: "text-violet-400" },
  ].filter((s) => s.value)

  return (
    <PanelBox title="Zahnfee" icon={<span className="text-sm">🦷</span>}>
      {briefing.error ? (
        <p className="text-xs text-rose-400 italic">{briefing.error}</p>
      ) : (
        <div className="flex flex-col gap-2">
          {sections.map((s) => (
            <div key={s.label}>
              <p className={`text-[10px] font-semibold uppercase tracking-wider ${s.color} mb-0.5`}>{s.label}</p>
              <p className="text-xs text-zinc-400 leading-snug line-clamp-3">{s.value}</p>
            </div>
          ))}
        </div>
      )}
      <Link to="/zahnfee" className="mt-3 block text-xs text-zinc-600 hover:text-zinc-400 transition-colors">
        {briefing.date} · Details →
      </Link>
    </PanelBox>
  )
}

export function BuddyLeftPanel() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [briefing, setBriefing] = useState<Briefing | null | undefined>(undefined)

  useEffect(() => {
    dashboardApi.summary().then(setSummary).catch(() => {})
    zahnfeeApi.briefing().then((r) => setBriefing(r.briefing)).catch(() => setBriefing(null))
  }, [])

  return (
    <div className="flex flex-col gap-4 w-60">
      <ZahnfeeBox briefing={briefing} />

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
