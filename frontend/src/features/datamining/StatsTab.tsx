import { useEffect, useState } from "react"
import { dataminingApi, type StatsDay, type StatsSession } from "./api"
import { fmtDateTime } from "./types"

function fmt(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M"
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "k"
  return String(n)
}

function CacheBar({ pct }: { pct: number }) {
  const color = pct >= 60 ? "bg-emerald-500" : pct >= 30 ? "bg-amber-500" : "bg-rose-500"
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-white/[8%] rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="tabular-nums text-zinc-400 w-10 text-right">{pct}%</span>
    </div>
  )
}

function DailyChart({ days }: { days: StatsDay[] }) {
  if (days.length === 0) return null
  const maxTokens = Math.max(...days.map((d) => d.input_tokens + d.cache_creation_tokens + d.cache_read_tokens), 1)

  return (
    <div className="rounded-xl border border-white/[6%] bg-black/20 overflow-hidden">
      <div className="px-3 py-2 border-b border-white/[6%] bg-white/[2%]">
        <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
          Token-Zeitreihe (Tage)
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/[6%] text-[10px] uppercase tracking-wider text-zinc-600">
              <th className="text-left px-3 py-2">Datum</th>
              <th className="text-right px-3 py-2">Sessions</th>
              <th className="text-right px-3 py-2">Input</th>
              <th className="text-right px-3 py-2">Output</th>
              <th className="text-right px-3 py-2">Cache-Read</th>
              <th className="px-3 py-2 min-w-[140px]">Cache-Hit</th>
              <th className="px-3 py-2 min-w-[120px]">Volumen</th>
            </tr>
          </thead>
          <tbody>
            {days.map((d) => {
              const total = d.input_tokens + d.cache_creation_tokens + d.cache_read_tokens
              const barPct = Math.round((total / maxTokens) * 100)
              return (
                <tr key={d.date} className="border-b border-white/[3%] hover:bg-white/[2%]">
                  <td className="px-3 py-2 text-zinc-400 whitespace-nowrap">{d.date}</td>
                  <td className="px-3 py-2 text-zinc-500 text-right">{d.session_count}</td>
                  <td className="px-3 py-2 text-zinc-400 text-right tabular-nums">{fmt(d.input_tokens)}</td>
                  <td className="px-3 py-2 text-zinc-400 text-right tabular-nums">{fmt(d.output_tokens)}</td>
                  <td className="px-3 py-2 text-emerald-400 text-right tabular-nums">{fmt(d.cache_read_tokens)}</td>
                  <td className="px-3 py-2"><CacheBar pct={d.cache_hit_pct} /></td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-white/[8%] rounded-full overflow-hidden">
                        <div className="h-full bg-violet-500 rounded-full" style={{ width: `${barPct}%` }} />
                      </div>
                      <span className="text-zinc-600 tabular-nums w-10 text-right">{fmt(total)}</span>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function LatestTable({ sessions, onSelect }: { sessions: StatsSession[]; onSelect: (id: string) => void }) {
  return (
    <div className="rounded-xl border border-white/[6%] bg-black/20 overflow-hidden">
      <div className="px-3 py-2 border-b border-white/[6%] bg-white/[2%]">
        <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
          Letzte Sessions
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/[6%] text-[10px] uppercase tracking-wider text-zinc-600">
              <th className="text-left px-3 py-2">Zuletzt</th>
              <th className="text-left px-3 py-2">Agent</th>
              <th className="text-left px-3 py-2">Titel</th>
              <th className="text-right px-3 py-2">Nachrichten</th>
              <th className="text-right px-3 py-2">Input</th>
              <th className="text-right px-3 py-2">Output</th>
              <th className="px-3 py-2 min-w-[130px]">Cache-Hit</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr
                key={s.session_id}
                onClick={() => onSelect(s.session_id)}
                className="border-b border-white/[3%] hover:bg-white/[3%] cursor-pointer transition-colors"
              >
                <td className="px-3 py-2 text-zinc-500 whitespace-nowrap">{fmtDateTime(s.updated_at)}</td>
                <td className="px-3 py-2 text-zinc-400 truncate max-w-[120px]">{s.agent_id}</td>
                <td className="px-3 py-2 text-zinc-300 truncate max-w-[200px]">{s.title ?? "—"}</td>
                <td className="px-3 py-2 text-zinc-500 text-right tabular-nums">{s.message_count}</td>
                <td className="px-3 py-2 text-zinc-400 text-right tabular-nums">{fmt(s.input_tokens)}</td>
                <td className="px-3 py-2 text-zinc-400 text-right tabular-nums">{fmt(s.output_tokens)}</td>
                <td className="px-3 py-2"><CacheBar pct={s.cache_hit_pct} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SessionDetailPanel({ sessionId, onClose }: { sessionId: string; onClose: () => void }) {
  const [detail, setDetail] = useState<import("./api").StatsSessionDetail | null>(null)

  useEffect(() => {
    dataminingApi.statsSession(sessionId).then(setDetail).catch(() => {})
  }, [sessionId])

  if (!detail) return (
    <div className="flex items-center justify-center h-32 text-zinc-600 text-sm">Lade…</div>
  )

  const rows: [string, string][] = [
    ["Agent", detail.agent_id],
    ["Status", detail.status],
    ["Erstellt", fmtDateTime(detail.created_at)],
    ["Zuletzt", fmtDateTime(detail.updated_at)],
    ["Nachrichten", String(detail.message_count)],
    ["Tool-Calls", String(detail.tool_call_count)],
    ["Compactions", String(detail.compaction_count)],
    ["Input Tokens", fmt(detail.input_tokens)],
    ["Output Tokens", fmt(detail.output_tokens)],
    ["Cache Creation", fmt(detail.cache_creation_tokens)],
    ["Cache Read", fmt(detail.cache_read_tokens)],
    ["Cache-Hit", `${detail.cache_hit_pct}%`],
  ]

  return (
    <div className="rounded-xl border border-white/[6%] bg-black/20 overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-white/[6%] bg-white/[2%]">
        <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
          Session-Detail
        </span>
        <span className="text-zinc-400 text-xs truncate flex-1">{detail.title ?? detail.session_id}</span>
        <button onClick={onClose} className="text-zinc-600 hover:text-zinc-300 text-xs">✕</button>
      </div>
      <div className="p-3 grid grid-cols-2 gap-x-6 gap-y-1.5">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between text-xs border-b border-white/[3%] py-1">
            <span className="text-zinc-500">{label}</span>
            <span className="text-zinc-300 tabular-nums">{value}</span>
          </div>
        ))}
      </div>
      <div className="px-3 pb-3">
        <CacheBar pct={detail.cache_hit_pct} />
      </div>
    </div>
  )
}

export function StatsTab({ active }: { active: boolean }) {
  const [latest, setLatest] = useState<StatsSession[]>([])
  const [daily, setDaily] = useState<StatsDay[]>([])
  const [days, setDays] = useState(14)
  const [loading, setLoading] = useState(true)
  const [selectedSession, setSelectedSession] = useState<string | null>(null)

  useEffect(() => {
    if (!active) return
    setLoading(true)
    Promise.all([
      dataminingApi.statsLatest(10).then((r) => setLatest(r.sessions)).catch(() => {}),
      dataminingApi.statsDaily(undefined, days).then((r) => setDaily(r.days)).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [active, days])

  if (loading) return (
    <div className="flex items-center justify-center h-32 text-zinc-600 text-sm">Lade…</div>
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-xs text-zinc-500">Zeitraum:</span>
        {[7, 14, 30].map((d) => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={`px-2 py-0.5 rounded text-xs transition-colors ${
              days === d ? "bg-amber-500/20 text-amber-300" : "bg-white/[4%] text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {d}d
          </button>
        ))}
      </div>

      <DailyChart days={daily} />

      <LatestTable sessions={latest} onSelect={setSelectedSession} />

      {selectedSession && (
        <SessionDetailPanel sessionId={selectedSession} onClose={() => setSelectedSession(null)} />
      )}
    </div>
  )
}
