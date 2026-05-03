import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { dataminingApi } from "./api"
import { fmtDateTime, type DmSession } from "./types"
import { SessionDrawer } from "./SessionDrawer"

export function SessionsTab({ active }: { active: boolean }) {
  const { t } = useTranslation("datamining")
  const [sessions, setSessions] = useState<DmSession[]>([])
  const [loading, setLoading] = useState(true)
  const [mirrorActive, setMirrorActive] = useState(false)
  const [selected, setSelected] = useState<DmSession | null>(null)

  useEffect(() => {
    if (!active) return
    dataminingApi.sessions()
      .then((d) => { setMirrorActive(d.active); setSessions(d.sessions) })
      .catch(() => setSessions([]))
      .finally(() => setLoading(false))
  }, [active])

  if (selected) {
    return <SessionDrawer session={selected} onClose={() => setSelected(null)} />
  }

  return (
    <div className="rounded-xl border border-white/[6%] bg-black/20 overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[6%] bg-white/[2%]">
        <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
          {t("sessions.title")}
        </span>
        <span className="text-[10px] text-zinc-600 ml-auto">{sessions.length} {t("entries")}</span>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-32 text-zinc-600 text-sm">{t("loading")}</div>
      ) : sessions.length === 0 ? (
        <div className="flex items-center justify-center h-32 text-zinc-600 text-sm">
          {mirrorActive ? t("sessions.no_sessions") : t("not_configured")}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/[6%] text-[10px] uppercase tracking-wider text-zinc-600">
                <th className="text-left px-3 py-2">{t("sessions.col_date")}</th>
                <th className="text-left px-3 py-2">{t("sessions.col_agent")}</th>
                <th className="text-left px-3 py-2">{t("sessions.col_user")}</th>
                <th className="text-left px-3 py-2">{t("sessions.col_title")}</th>
                <th className="text-right px-3 py-2">{t("sessions.col_events")}</th>
                <th className="text-left px-3 py-2">{t("sessions.col_status")}</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr
                  key={s.id}
                  onClick={() => setSelected(s)}
                  className="border-b border-white/[3%] hover:bg-white/[3%] cursor-pointer transition-colors"
                >
                  <td className="px-3 py-2 text-zinc-500 whitespace-nowrap">{fmtDateTime(s.updated_at)}</td>
                  <td className="px-3 py-2 text-zinc-400 truncate max-w-[120px]">{s.agent_name ?? "—"}</td>
                  <td className="px-3 py-2 text-zinc-500 truncate max-w-[100px]">{s.username ?? "—"}</td>
                  <td className="px-3 py-2 text-zinc-300 truncate max-w-[200px]">{s.title ?? "—"}</td>
                  <td className="px-3 py-2 text-zinc-500 text-right">{s.event_count}</td>
                  <td className="px-3 py-2">
                    <StatusBadge status={s.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status }: { status: string | null }) {
  const colors: Record<string, string> = {
    active:    "text-emerald-400 bg-emerald-500/10",
    completed: "text-zinc-400 bg-zinc-500/10",
    error:     "text-rose-400 bg-rose-500/10",
  }
  const cls = colors[status ?? ""] ?? "text-zinc-500 bg-zinc-500/10"
  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${cls}`}>
      {status ?? "—"}
    </span>
  )
}
