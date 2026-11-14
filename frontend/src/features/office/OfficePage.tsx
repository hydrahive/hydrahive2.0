import { useTranslation } from "react-i18next"
import { ExternalLink, X } from "lucide-react"
import { useAgentActivity } from "@/features/chat/useAgentActivity"
import { EmptyState } from "@/shared/EmptyState"
import { charImageForGroup, OFFICE_BACKGROUND } from "./officeAssets"
import { standupStats } from "./standupStats"
import { useTraceDrawer } from "./useTraceDrawer"

/** Spec docs/specs/agent-office.md — Etappe 3: Büro-Hintergrund + Charakter-Sprite je
 *  Template-Gruppe. Feste Sitzplätze (kein Pathfinding), Verbindungslinie zum Auftraggeber,
 *  Fortschrittsring + Sprechblase, Klick öffnet den bestehenden Trace-Drawer. */

// Feste Sitzplatz-Raster (in % der Bürofläche) — reicht für die üblichen 1–9 gleichzeitig
// laufenden Agenten; bei mehr wird einfach gewrappt (modulo).
const SEATS: Array<{ x: number; y: number }> = [
  { x: 14, y: 60 }, { x: 38, y: 42 }, { x: 62, y: 60 }, { x: 86, y: 42 },
  { x: 26, y: 78 }, { x: 50, y: 78 }, { x: 74, y: 78 }, { x: 14, y: 30 }, { x: 86, y: 78 },
]

export function OfficePage() {
  const { t } = useTranslation("office")
  const { running } = useAgentActivity(true)
  const drawer = useTraceDrawer()

  if (running.length === 0) {
    return (
      <EmptyState
        mood="sleeping"
        title={t("empty.title", { defaultValue: "Gerade arbeitet niemand" })}
        hint={t("empty.hint", { defaultValue: "Sobald ein Agent oder Spezialist läuft, erscheint er hier." })}
      />
    )
  }

  const byId = new Map(running.map((a) => [a.session_id, a]))
  const seatFor = new Map(running.map((a, i) => [a.session_id, SEATS[i % SEATS.length]]))
  const openAgent = drawer.openSessionId ? byId.get(drawer.openSessionId) : undefined
  const stats = standupStats(running)

  return (
    <div className="space-y-3">
      <div
        className="flex items-center gap-4 text-xs text-zinc-400 rounded-lg border border-white/10 bg-white/[3%] px-3 py-2"
        data-standup-total={stats.total}
        data-standup-delegated={stats.delegated}
        data-standup-errored={stats.errored}
      >
        <span>{t("standup.total", { count: stats.total, defaultValue: "{{count}} laufen" })}</span>
        {stats.delegated > 0 && (
          <span>{t("standup.delegated", { count: stats.delegated, defaultValue: "{{count}} davon beauftragt" })}</span>
        )}
        {stats.errored > 0 && (
          <span className="text-red-400">{t("standup.errored", { count: stats.errored, defaultValue: "{{count}} mit Fehler" })}</span>
        )}
      </div>

      <div className="relative rounded-xl overflow-hidden border border-white/10 min-h-[560px]">
        <img src={OFFICE_BACKGROUND} alt="" aria-hidden="true" className="absolute inset-0 w-full h-full object-cover brightness-[0.78] saturate-[0.9]" />
        <div className="absolute inset-0 bg-gradient-to-b from-black/10 to-black/45" />

        {/* Verbindungslinien zum Auftraggeber */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" aria-hidden="true">
          {running.filter((a) => a.parent_session_id && seatFor.has(a.parent_session_id)).map((a) => {
            const from = seatFor.get(a.parent_session_id as string)!
            const to = seatFor.get(a.session_id)!
            return (
              <line
                key={a.session_id}
                x1={`${from.x}%`} y1={`${from.y + 6}%`}
                x2={`${to.x}%`} y2={`${to.y + 6}%`}
                stroke="rgba(255,255,255,0.35)" strokeWidth={1.5} strokeDasharray="4 4"
              />
            )
          })}
        </svg>

        {running.map((a) => {
          const seat = seatFor.get(a.session_id)!
          const progress = a.max_iterations ? Math.min(1, (a.iteration ?? 0) / a.max_iterations) : 0
          const img = charImageForGroup(a.template_group)
          return (
            <button
              key={a.session_id}
              type="button"
              data-agent-card={a.session_id}
              data-parent={a.parent_session_id ?? undefined}
              onClick={() => drawer.open(a.session_id)}
              className="absolute flex flex-col items-center w-32 -translate-x-1/2 group z-10"
              style={{ left: `${seat.x}%`, top: `${seat.y}%` }}
            >
              {a.last_tool_result_summary && (
                <div className="mb-1 rounded-md bg-black/80 border border-white/15 px-2 py-1 text-[10px] text-zinc-100 text-center line-clamp-2 max-w-[140px]">
                  {a.last_tool_result_summary}
                </div>
              )}
              <div className="relative">
                <img src={img} alt="" aria-hidden="true" className="w-20 h-20 object-contain drop-shadow-[0_6px_8px_rgba(0,0,0,0.5)] transition-transform group-hover:-translate-y-0.5" />
                {a.max_iterations ? (
                  <svg className="absolute -top-1 -right-1 w-6 h-6 -rotate-90">
                    <circle cx="12" cy="12" r="10" className="stroke-white/15" fill="none" strokeWidth={3} />
                    <circle
                      cx="12" cy="12" r="10" className="stroke-emerald-400" fill="none" strokeWidth={3}
                      strokeDasharray={2 * Math.PI * 10} strokeDashoffset={2 * Math.PI * 10 * (1 - progress)}
                      strokeLinecap="round"
                    />
                  </svg>
                ) : null}
              </div>
              <span className="mt-1 text-xs font-medium text-white drop-shadow">{a.name}</span>
              {a.project_id && <span className="text-[10px] text-zinc-300 truncate max-w-full drop-shadow">{a.project_id}</span>}
              {a.parent_session_id && (
                <span className="text-[10px] text-zinc-400 drop-shadow">
                  {t("card.delegated_by", { defaultValue: "beauftragt von" })} {byId.get(a.parent_session_id)?.name ?? a.parent_session_id}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {openAgent && (
        <div role="dialog" aria-label={openAgent.name} className="fixed inset-y-0 right-0 w-80 bg-zinc-900 border-l border-white/10 shadow-xl z-50 flex flex-col">
          <div className="flex items-center justify-between p-3 border-b border-white/10">
            <span className="font-medium text-sm">{openAgent.name}</span>
            <button type="button" aria-label={t("drawer.close", { defaultValue: "Schließen" })} onClick={drawer.close}>
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {drawer.calls.length === 0 && (
              <div className="text-xs text-zinc-500">{t("drawer.empty", { defaultValue: "Noch keine Tool-Aufrufe." })}</div>
            )}
            {drawer.calls.map((c) => (
              <div key={c.id} className="text-xs border-b border-white/5 pb-1.5">
                <div className="flex items-center justify-between">
                  <span className={c.status === "error" ? "text-red-400" : "text-zinc-200"}>{c.tool_name}</span>
                  {c.duration_ms != null && <span className="text-zinc-500">{c.duration_ms}ms</span>}
                </div>
                {c.github_link && (
                  <a
                    href={c.github_link}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 inline-flex items-center gap-1 text-emerald-400 hover:text-emerald-300"
                  >
                    <ExternalLink className="w-3 h-3" />
                    {t("drawer.github_link", { defaultValue: "PR/Issue öffnen" })}
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
