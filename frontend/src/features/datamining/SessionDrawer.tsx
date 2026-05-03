import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ArrowLeft } from "lucide-react"
import { dataminingApi } from "./api"
import { fmtTime, fmtDateTime, TYPE_COLORS, type DmSession, type DmSessionEvent } from "./types"

interface Props {
  session: DmSession
  onClose: () => void
}

export function SessionDrawer({ session, onClose }: Props) {
  const { t } = useTranslation("datamining")
  const [events, setEvents] = useState<DmSessionEvent[] | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    dataminingApi.sessionDetail(session.id)
      .then((d) => setEvents(d.events))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false))
  }, [session.id])

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <button
          onClick={onClose}
          className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          <ArrowLeft size={13} />
          {t("session_detail.back")}
        </button>
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium text-zinc-200 truncate block">
            {session.title || t("session_detail.untitled")}
          </span>
          <div className="flex items-center gap-3 text-[10px] text-zinc-500 mt-0.5">
            {session.agent_name && <span>{session.agent_name}</span>}
            {session.username && <span>{session.username}</span>}
            <span>{fmtDateTime(session.started_at)}</span>
            {events !== null && (
              <span>{events.length} {t("session_detail.events")}</span>
            )}
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-white/[6%] bg-black/20 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-40 text-zinc-600 text-sm">{t("loading")}</div>
        ) : !events || events.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-zinc-600 text-sm">{t("empty")}</div>
        ) : (
          <div className="max-h-[32rem] overflow-y-auto divide-y divide-white/[3%]">
            {events.map((e, i) => (
              <SessionEvent key={i} event={e} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function SessionEvent({ event: e }: { event: DmSessionEvent }) {
  const [expanded, setExpanded] = useState(false)
  const content = e.text || e.tool_output || ""
  const isLong = content.length > 300

  return (
    <div className="px-3 py-2 hover:bg-white/[2%]">
      <div className="flex items-center gap-2 text-[10px] mb-1">
        <span className="text-zinc-600 shrink-0">{fmtTime(e.created_at)}</span>
        <span className={`shrink-0 px-1 rounded font-medium ${TYPE_COLORS[e.event_type] ?? "text-zinc-400 bg-zinc-500/10"}`}>
          {e.event_type}
        </span>
        {e.tool_name && <span className="text-zinc-500">{e.tool_name}</span>}
        {e.is_error && <span className="text-rose-400">ERR</span>}
      </div>
      {content && (
        <div>
          <pre className={`text-[11px] text-zinc-400 font-mono whitespace-pre-wrap leading-relaxed ${!expanded && isLong ? "line-clamp-4" : ""}`}>
            {content}
          </pre>
          {isLong && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-[10px] text-zinc-600 hover:text-zinc-400 mt-0.5 transition-colors"
            >
              {expanded ? "↑ weniger" : "↓ mehr"}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
