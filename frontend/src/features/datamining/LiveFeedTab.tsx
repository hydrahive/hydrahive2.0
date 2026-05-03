import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { RefreshCw } from "lucide-react"
import { dataminingApi } from "./api"
import { fmtTime, TYPE_COLORS, type DmEvent } from "./types"

export function LiveFeedTab({ active }: { active: boolean }) {
  const { t } = useTranslation("datamining")
  const [events, setEvents] = useState<DmEvent[]>([])
  const [mirrorActive, setMirrorActive] = useState(false)
  const [loading, setLoading] = useState(true)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  async function load() {
    try {
      const data = await dataminingApi.events(100)
      setMirrorActive(data.active)
      setEvents(data.events)
    } catch {
      // mirror not reachable
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!active) return
    load()
    intervalRef.current = setInterval(load, 5000)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [active])

  return (
    <div className="rounded-xl border border-white/[6%] bg-black/20 overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[6%] bg-white/[2%]">
        <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
          {t("live_feed")}
        </span>
        <span className="text-[10px] text-zinc-600 ml-auto">{events.length} {t("entries")}</span>
        <button onClick={load} className="text-zinc-500 hover:text-zinc-300 transition-colors ml-1">
          <RefreshCw size={11} />
        </button>
      </div>

      <div className="h-80 overflow-y-auto font-mono text-[11px] leading-relaxed">
        {loading ? (
          <div className="flex items-center justify-center h-full text-zinc-600">{t("loading")}</div>
        ) : events.length === 0 ? (
          <div className="flex items-center justify-center h-full text-zinc-600">
            {mirrorActive ? t("empty") : t("not_configured")}
          </div>
        ) : (
          events.map((e) => (
            <div key={e.id} className="flex items-start gap-2 px-3 py-0.5 hover:bg-white/[3%] border-b border-white/[3%]">
              <span className="text-zinc-600 shrink-0 w-20">{fmtTime(e.created_at)}</span>
              <span className="text-zinc-500 shrink-0 w-20 truncate">{e.username ?? "—"}</span>
              <span className="text-zinc-400 shrink-0 w-24 truncate">{e.agent_name ?? "—"}</span>
              <span className={`shrink-0 px-1 rounded text-[10px] font-medium ${TYPE_COLORS[e.event_type] ?? "text-zinc-400 bg-zinc-500/10"}`}>
                {e.event_type}
              </span>
              {e.tool_name && <span className="text-zinc-500 shrink-0">{e.tool_name}</span>}
              {e.is_error && <span className="text-rose-400 shrink-0">ERR</span>}
              <span className="text-zinc-400 truncate min-w-0">{e.snippet ?? ""}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
