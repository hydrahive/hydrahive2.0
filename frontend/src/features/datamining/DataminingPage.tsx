import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Pickaxe, RefreshCw } from "lucide-react"
import { api } from "@/shared/api-client"

interface Event {
  id: string
  session_id: string
  username: string | null
  agent_name: string | null
  event_type: string
  created_at: string
  tool_name: string | null
  is_error: boolean | null
  snippet: string | null
}

const TYPE_COLORS: Record<string, string> = {
  user_input:     "text-blue-300 bg-blue-500/10",
  assistant_text: "text-violet-300 bg-violet-500/10",
  tool_call:      "text-amber-300 bg-amber-500/10",
  tool_result:    "text-emerald-300 bg-emerald-500/10",
  thinking:       "text-zinc-400 bg-zinc-500/10",
  compaction:     "text-fuchsia-300 bg-fuchsia-500/10",
}

function fmtTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString("de", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
  } catch {
    return ts.slice(11, 19)
  }
}

export function DataminingPage() {
  const { t } = useTranslation("datamining")
  const [events, setEvents] = useState<Event[]>([])
  const [active, setActive] = useState(false)
  const [loading, setLoading] = useState(true)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  async function load() {
    try {
      const data = await api.get<{ active: boolean; events: Event[] }>("/datamining/events?limit=100")
      setActive(data.active)
      setEvents(data.events)
    } catch {
      // mirror not reachable
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    intervalRef.current = setInterval(load, 5000)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [])

  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Pickaxe className="text-amber-400" size={20} />
          <div>
            <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
            <p className="text-xs text-zinc-500 mt-0.5">{t("subtitle")}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`flex items-center gap-1.5 text-xs ${active ? "text-emerald-400" : "text-zinc-500"}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${active ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.7)]" : "bg-zinc-600"}`} />
            {active ? t("status_active") : t("status_inactive")}
          </span>
          <button onClick={load} className="text-zinc-500 hover:text-zinc-300 transition-colors">
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-white/[6%] bg-black/20 overflow-hidden">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[6%] bg-white/[2%]">
          <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
            {t("live_feed")}
          </span>
          <span className="text-[10px] text-zinc-600 ml-auto">
            {events.length} {t("entries")}
          </span>
        </div>

        <div className="h-64 overflow-y-auto font-mono text-[11px] leading-relaxed">
          {loading ? (
            <div className="flex items-center justify-center h-full text-zinc-600">{t("loading")}</div>
          ) : events.length === 0 ? (
            <div className="flex items-center justify-center h-full text-zinc-600">
              {active ? t("empty") : t("not_configured")}
            </div>
          ) : (
            events.map((e) => (
              <div key={e.id} className="flex items-start gap-2 px-3 py-0.5 hover:bg-white/[3%] border-b border-white/[3%]">
                <span className="text-zinc-600 shrink-0 w-20">{fmtTime(e.created_at)}</span>
                <span className="text-zinc-500 shrink-0 w-20 truncate">{e.username ?? "—"}</span>
                <span className={`shrink-0 px-1 rounded text-[10px] font-medium ${TYPE_COLORS[e.event_type] ?? "text-zinc-400 bg-zinc-500/10"}`}>
                  {e.event_type}
                </span>
                {e.tool_name && (
                  <span className="text-zinc-500 shrink-0">{e.tool_name}</span>
                )}
                {e.is_error && (
                  <span className="text-rose-400 shrink-0">ERR</span>
                )}
                <span className="text-zinc-400 truncate min-w-0">{e.snippet ?? ""}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
