import { useTranslation } from "react-i18next"
import { X } from "lucide-react"
import { useAgentActivity } from "@/features/chat/useAgentActivity"
import { EmptyState } from "@/shared/EmptyState"
import { useTraceDrawer } from "./useTraceDrawer"

/** Spec docs/specs/agent-office.md — Etappe 2: Seite ohne Grafik, einfache Karten + Drawer.
 *  Platzhalter-Design (Hintergrund/Charakter-Sprites kommen in Etappe 3). */
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
  const openAgent = drawer.openSessionId ? byId.get(drawer.openSessionId) : undefined

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {running.map((a) => {
          const progress = a.max_iterations ? Math.min(1, (a.iteration ?? 0) / a.max_iterations) : 0
          return (
            <button
              key={a.session_id}
              type="button"
              data-agent-card={a.session_id}
              data-parent={a.parent_session_id ?? undefined}
              onClick={() => drawer.open(a.session_id)}
              className="text-left rounded-lg border border-white/10 bg-white/[3%] hover:bg-white/[6%] p-3 transition"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-sm">{a.name}</span>
                {a.project_id && <span className="text-[10px] text-zinc-500 truncate">{a.project_id}</span>}
              </div>
              {a.parent_session_id && (
                <div className="text-[10px] text-zinc-500 mt-0.5">
                  {t("card.delegated_by", { defaultValue: "beauftragt von" })} {byId.get(a.parent_session_id)?.name ?? a.parent_session_id}
                </div>
              )}
              {a.last_tool_result_summary && (
                <div className="text-xs text-zinc-400 mt-1.5 line-clamp-2">{a.last_tool_result_summary}</div>
              )}
              {a.max_iterations ? (
                <div className="mt-2 h-1 rounded bg-white/10 overflow-hidden">
                  <div className="h-full bg-emerald-500/70" style={{ width: `${progress * 100}%` }} />
                </div>
              ) : null}
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
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
