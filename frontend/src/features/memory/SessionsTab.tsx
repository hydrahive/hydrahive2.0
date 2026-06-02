import { useEffect, useState } from "react"
import type { CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { ChevronDown, ChevronRight } from "lucide-react"
import { rgbFor } from "@/shared/colors"
import { memoryApi } from "./api"
import type { MemorySession, CompressedObservation } from "./types"

interface Props {
  agentId: string
}

export function SessionsTab({ agentId }: Props) {
  const { t } = useTranslation("memory")
  const [sessions, setSessions] = useState<MemorySession[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [observations, setObservations] = useState<Record<string, CompressedObservation[]>>({})
  const [obsLoading, setObsLoading] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    memoryApi.getSessions(agentId, { limit: 100 })
      .then((res) => { setSessions(res.sessions); setTotal(res.total) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [agentId])

  async function toggleSession(sessionId: string) {
    if (expanded === sessionId) {
      setExpanded(null)
      return
    }
    setExpanded(sessionId)
    if (observations[sessionId]) return
    setObsLoading(sessionId)
    try {
      const res = await memoryApi.getObservations(agentId, sessionId)
      setObservations((cur) => ({ ...cur, [sessionId]: res.observations }))
    } catch {
      setObservations((cur) => ({ ...cur, [sessionId]: [] }))
    } finally {
      setObsLoading(null)
    }
  }

  if (loading) return <p className="text-xs text-zinc-600 p-4">{t("loading")}</p>

  return (
    <div className="space-y-3 p-4">
      <p className="text-[10px] text-zinc-600">{t("session_count", { count: total })}</p>

      {sessions.length === 0 ? (
        <p className="text-xs text-zinc-600 text-center py-8">{t("no_sessions")}</p>
      ) : (
        <div className="space-y-1.5">
          {sessions.map((s) => {
            const open = expanded === s.session_id
            return (
              <div
                key={s.session_id}
                className="box overflow-hidden"
                style={{ "--c": rgbFor("/agents") } as CSSProperties}
              >
                {/* Row */}
                <button
                  onClick={() => toggleSession(s.session_id)}
                  className="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-white/[2%] transition-colors"
                >
                  <span className="text-zinc-600 flex-shrink-0">
                    {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  </span>

                  <div className="flex-1 min-w-0 grid grid-cols-[1fr_auto_auto_auto_auto] gap-x-4 items-center">
                    <p className="text-xs text-zinc-300 truncate" title={s.first_prompt ?? undefined}>
                      {s.first_prompt ?? <span className="text-zinc-700 italic">{t("no_prompt")}</span>}
                    </p>
                    <StatusPill status={s.status} />
                    <span className="text-[10px] text-zinc-600 font-mono whitespace-nowrap">
                      {s.observation_count} obs
                    </span>
                    {s.has_crystal && (
                      <span className="text-[10px] text-violet-400">💎</span>
                    )}
                    <span className="text-[10px] text-zinc-700 whitespace-nowrap">
                      {s.started_at ? formatDate(s.started_at) : "—"}
                    </span>
                  </div>
                </button>

                {/* Observations */}
                {open && (
                  <div className="border-t border-white/[4%] px-4 py-3 space-y-2">
                    {obsLoading === s.session_id ? (
                      <p className="text-xs text-zinc-600">{t("loading")}</p>
                    ) : (observations[s.session_id] ?? []).length === 0 ? (
                      <p className="text-xs text-zinc-700">{t("no_observations")}</p>
                    ) : (
                      (observations[s.session_id] ?? []).map((obs) => (
                        <ObservationCard key={obs.id} obs={obs} />
                      ))
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function ObservationCard({ obs }: { obs: CompressedObservation }) {
  const { t } = useTranslation("memory")
  return (
    <div className="box overflow-hidden px-3 py-2 space-y-1.5" style={{ "--c": rgbFor("/agents") } as CSSProperties}>
      <div className="flex items-center gap-2">
        <TypeBadge type={obs.type} />
        <p className="text-xs font-medium text-zinc-200">{obs.title}</p>
        <span className="ml-auto text-[10px] text-zinc-700">
          {t("importance")}: {obs.importance}
        </span>
      </div>
      {obs.narrative && (
        <p className="text-[11px] text-zinc-400 leading-relaxed">{obs.narrative}</p>
      )}
      {obs.facts.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {obs.facts.map((f, i) => (
            <span key={i} className="px-1.5 py-0.5 rounded bg-zinc-800 text-[10px] text-zinc-500">{f}</span>
          ))}
        </div>
      )}
      {obs.files.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {obs.files.map((f, i) => (
            <span key={i} className="px-1.5 py-0.5 rounded bg-zinc-800 text-[10px] font-mono text-zinc-600">{f}</span>
          ))}
        </div>
      )}
    </div>
  )
}

function StatusPill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    closed: "bg-zinc-500/10 text-zinc-500 border-zinc-500/20",
    crystallized: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  }
  const cls = colors[status] ?? "bg-zinc-500/10 text-zinc-500 border-zinc-500/20"
  return (
    <span className={`px-1.5 py-0.5 rounded-full border text-[10px] flex-shrink-0 ${cls}`}>
      {status}
    </span>
  )
}

function TypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    code_change: "text-sky-400",
    decision: "text-amber-400",
    error: "text-red-400",
    insight: "text-violet-400",
  }
  return (
    <span className={`text-[10px] font-mono ${colors[type] ?? "text-zinc-500"}`}>[{type}]</span>
  )
}

function formatDate(iso: string): string {
  try { return new Date(iso).toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" }) }
  catch { return iso }
}
