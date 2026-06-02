import { useEffect, useState, type CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { Activity, Loader2 } from "lucide-react"
import { dashboardApi, type DashboardSummary } from "@/features/dashboard/api"
import { zahnfeeApi, type Briefing } from "@/features/zahnfee/api"
import { Link } from "react-router-dom"

function PanelBox({ title, icon, c, children }: { title: string; icon: React.ReactNode; c: string; children: React.ReactNode }) {
  return (
    <div className="box overflow-hidden" style={{ "--c": c } as CSSProperties}>
      <div className="box-h">
        <span className="ic">{icon}</span>
        <span className="t">{title}</span>
      </div>
      <div className="box-b">{children}</div>
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
  const { t } = useTranslation("buddy")
  if (briefing === undefined) {
    return (
      <PanelBox title="Zahnfee" c="139 92 246" icon={<span className="text-sm">🦷</span>}>
        <Loader2 size={14} className="text-zinc-600 animate-spin" />
      </PanelBox>
    )
  }
  if (!briefing) {
    return (
      <PanelBox title="Zahnfee" c="139 92 246" icon={<span className="text-sm">🦷</span>}>
        <div className="flex flex-col items-center text-center gap-2">
          <img src="/illustrations/empty-briefing.png" alt="" width={84} height={84}
            className="object-contain opacity-95 drop-shadow-[0_0_16px_rgba(139,92,246,0.3)] select-none pointer-events-none" />
          <p className="text-xs text-zinc-500 italic leading-relaxed">{t("left_panel.no_briefing")}</p>
          <Link to="/zahnfee" className="text-xs text-violet-400 hover:text-violet-300 transition-colors">{t("left_panel.setup")}</Link>
        </div>
      </PanelBox>
    )
  }
  const sections = [
    { label: t("briefing.open"), value: briefing.open_items, color: "text-amber-400" },
    { label: t("briefing.went_well"), value: briefing.went_well, color: "text-emerald-400" },
    { label: t("briefing.went_badly"), value: briefing.went_badly, color: "text-rose-400" },
    { label: t("briefing.today"), value: briefing.today, color: "text-violet-400" },
  ].filter((s) => s.value)

  return (
    <PanelBox title="Zahnfee" c="139 92 246" icon={<span className="text-sm">🦷</span>}>
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
  const { t } = useTranslation("buddy")
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [briefing, setBriefing] = useState<Briefing | null | undefined>(undefined)

  useEffect(() => {
    dashboardApi.summary().then(setSummary).catch(() => {})
    zahnfeeApi.briefing().then((r) => setBriefing(r.briefing)).catch(() => setBriefing(null))
  }, [])

  return (
    <div className="flex flex-col gap-4 w-60">
      <ZahnfeeBox briefing={briefing} />

      <PanelBox title="System" c="20 184 166" icon={<Activity size={13} className="text-teal-300" />}>
        {!summary ? (
          <Loader2 size={14} className="text-zinc-600 animate-spin" />
        ) : (
          <div>
            <StatRow label={t("left_panel.tokens_today")} value={summary.stats.tokens_today.toLocaleString()} />
            <StatRow label={t("left_panel.active_sessions")} value={summary.stats.active_sessions} />
            <StatRow label={t("left_panel.tool_calls")} value={summary.stats.tool_calls_today} />
            <StatRow
              label={t("left_panel.server")}
              value={`${summary.stats.servers_running} / ${summary.stats.servers_total}`}
              accent={summary.stats.servers_running > 0 ? "text-emerald-400" : "text-zinc-500"}
            />
            <StatRow
              label={t("left_panel.backend")}
              value={summary.health.backend.ok ? t("left_panel.backend_ok") : t("left_panel.backend_error")}
              accent={summary.health.backend.ok ? "text-emerald-400" : "text-rose-400"}
            />
          </div>
        )}
      </PanelBox>
    </div>
  )
}
