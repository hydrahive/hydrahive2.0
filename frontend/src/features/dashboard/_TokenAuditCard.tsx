import { AlertTriangle, Coins, Cpu, TrendingUp } from "lucide-react"
import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { cn } from "@/shared/cn"
import { analyticsApi, type AnalyticsOverview } from "./api"

const REFRESH_MS = 30_000

export function TokenAuditCard() {
  const [data, setData] = useState<AnalyticsOverview | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    let alive = true
    async function load() {
      try {
        const o = await analyticsApi.overview()
        if (alive) { setData(o); setError(false) }
      } catch {
        if (alive) setError(true)
      }
    }
    load()
    const t = setInterval(load, REFRESH_MS)
    return () => { alive = false; clearInterval(t) }
  }, [])

  if (error) {
    return (
      <Shell>
        <p className="text-xs text-zinc-500 py-2 text-center">Analytics nicht verfügbar</p>
      </Shell>
    )
  }
  if (!data) {
    return (
      <Shell>
        <p className="text-xs text-zinc-500 py-2 text-center">…</p>
      </Shell>
    )
  }

  const today = data.today
  const last7 = data.last_7d
  const todayTokens = (today.input_tokens || 0) + (today.output_tokens || 0)
  // Cache-Hit = wie viel vom INPUT kam aus dem Cache. Anthropic zählt input
  // (=neue Tokens), cache_read und cache_creation getrennt — alle drei sind
  // der Gesamt-Input. Cache-Hit-Ratio = cache_read / (input + cache_read +
  // cache_creation). Output zählt nicht (das ist Generation, nicht Input).
  const totalInput7d = (last7.input_tokens || 0)
    + (last7.cache_read_tokens || 0)
    + (last7.cache_creation_tokens || 0)
  const cacheRatio7d = totalInput7d > 0
    ? Math.round(100 * (last7.cache_read_tokens || 0) / totalInput7d)
    : 0

  return (
    <Shell>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-3">
        <Tile icon={Coins} label="Heute Tokens"
          value={formatNumber(todayTokens)}
          sub={`${today.llm_calls || 0} LLM-Calls`}
          from="from-amber-500" to="to-orange-600" />
        <Tile icon={TrendingUp} label="Heute Kosten"
          value={formatCents(today.cost_micros || 0)}
          sub={`7 Tage: ${formatCents(last7.cost_micros || 0)}`}
          from="from-emerald-500" to="to-teal-600" />
        <Tile icon={Cpu} label="Cache-Hit (7d)"
          value={`${cacheRatio7d}%`}
          sub={`${formatNumber(last7.cache_read_tokens || 0)} cache_read`}
          from="from-sky-500" to="to-cyan-600" />
        <Tile icon={AlertTriangle} label="Heute Fehler"
          value={String((today.errors || 0) + (today.tool_errors || 0))}
          sub={`${today.compactions || 0} Compactions`}
          from="from-rose-500" to="to-pink-600" />
      </div>

      {data.top_cost_sessions.length > 0 && (
        <div>
          <h4 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500 mb-1">
            Teuerste Sessions (7 Tage)
          </h4>
          <div className="space-y-0.5">
            {data.top_cost_sessions.map((s) => (
              <Link key={s.session_id} to={`/analytics/session/${s.session_id}`}
                className="flex items-center gap-2 px-1.5 py-1 rounded-md hover:bg-white/[4%] transition-colors">
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] text-zinc-200 truncate leading-tight">
                    {s.title || `Session ${s.session_id.slice(0, 8)}`}
                  </p>
                  <p className="text-[10px] text-zinc-600 truncate leading-tight">
                    {s.llm_calls} Calls · {formatNumber((s.input_tokens || 0) + (s.output_tokens || 0))} Tokens
                    {s.errors > 0 ? ` · ${s.errors} Fehler` : ""}
                  </p>
                </div>
                <span className="text-[11px] font-semibold text-amber-400 flex-shrink-0">
                  {formatCents(s.cost_micros)}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {data.by_model.length > 0 && (
        <div className="mt-3 pt-3 border-t border-white/[6%]">
          <h4 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500 mb-1">
            Nach Modell (7 Tage)
          </h4>
          <div className="space-y-0.5">
            {data.by_model.slice(0, 5).map((m) => (
              <div key={m.model} className="flex items-center gap-2 px-1.5 py-0.5">
                <p className="text-[11px] text-zinc-300 flex-1 truncate font-mono">{m.model}</p>
                <span className="text-[10px] text-zinc-500">{m.calls}×</span>
                <span className="text-[11px] font-semibold text-amber-400 w-16 text-right">
                  {formatCents(m.cost_micros)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Shell>
  )
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-white/[8%] bg-white/[3%] p-4">
      <h3 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500 mb-2">
        Token-Audit
      </h3>
      {children}
    </div>
  )
}

function Tile(props: {
  icon: React.ComponentType<{ size?: number; className?: string }>
  label: string
  value: string
  sub?: string
  from: string
  to: string
}) {
  return (
    <div className="rounded-lg border border-white/[8%] bg-white/[3%] px-3 py-2 flex items-center gap-2.5">
      <div className={cn(
        "relative w-7 h-7 rounded-full flex items-center justify-center bg-gradient-to-br shrink-0",
        props.from, props.to,
      )}>
        <props.icon size={13} className="text-white" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-zinc-500 text-[9px] uppercase tracking-wide truncate">{props.label}</p>
        <p className="text-base font-bold text-white leading-tight">{props.value}</p>
        {props.sub && <p className="text-[10px] text-zinc-600 truncate">{props.sub}</p>}
      </div>
    </div>
  )
}

function formatNumber(n: number): string {
  if (n < 1000) return String(n)
  if (n < 1_000_000) return `${(n / 1000).toFixed(1)}k`
  return `${(n / 1_000_000).toFixed(1)}M`
}

function formatCents(micros: number): string {
  // 1 Cent = 1000 Micros → cents = micros / 1000 → € = cents / 100
  const euro = micros / 100_000
  if (euro < 0.01) return `${(micros / 1000).toFixed(2)}¢`
  if (euro < 1) return `${(euro * 100).toFixed(1)}¢`
  return `€${euro.toFixed(2)}`
}
