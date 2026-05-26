import { ArrowLeft, MessageSquare } from "lucide-react"
import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { analyticsApi, type SessionDetail } from "./api"

export function SessionDetailPage() {
  const { sid } = useParams<{ sid: string }>()
  const [data, setData] = useState<SessionDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sid) return
    let alive = true
    analyticsApi.sessionDetail(sid)
      .then((d) => { if (alive) setData(d) })
      .catch((e: Error) => { if (alive) setError(e.message || "Fehler") })
    return () => { alive = false }
  }, [sid])

  if (error) return <div className="p-4 text-red-400">Fehler: {error}</div>
  if (!data) return <div className="p-4 text-zinc-500">…</div>

  const s = data.session
  const m = data.metrics

  return (
    <div className="space-y-4 max-w-7xl">
      <div className="flex items-center gap-3">
        <Link to="/dashboard" className="text-zinc-500 hover:text-zinc-300">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-xl font-bold text-white">{s.title || `Session ${s.id.slice(0, 8)}`}</h1>
          <p className="text-xs text-zinc-500">
            Agent: {s.agent_name || s.agent_id || "?"} · User: {s.user_id || "?"} · Status: {s.status}
          </p>
        </div>
        <div className="ml-auto">
          <Link to={`/werkstatt?session=${s.id}`}
            className="text-xs px-3 py-1.5 rounded-md bg-violet-500/20 text-violet-300 hover:bg-violet-500/30 flex items-center gap-1.5">
            <MessageSquare size={12} />
            Im Chat öffnen
          </Link>
        </div>
      </div>

      {m && <MetricsRow m={m} />}

      <Section title={`LLM-Calls (${data.llm_calls.length})`}>
        <LlmCallsTable rows={data.llm_calls} />
      </Section>

      {data.tool_calls.length > 0 && (
        <Section title={`Tool-Calls (${data.tool_calls.length})`}>
          <ToolCallsTable rows={data.tool_calls} />
        </Section>
      )}

      {data.compactions.length > 0 && (
        <Section title={`Compactions (${data.compactions.length})`}>
          <CompactionsTable rows={data.compactions} />
        </Section>
      )}

      {data.errors.length > 0 && (
        <Section title={`Fehler (${data.errors.length})`}>
          <ErrorsTable rows={data.errors} />
        </Section>
      )}
    </div>
  )
}

function MetricsRow({ m }: { m: NonNullable<SessionDetail["metrics"]> }) {
  const totalInput = (m.input_tokens || 0) + (m.cache_read_tokens || 0) + (m.cache_creation_tokens || 0)
  const cacheRatio = totalInput > 0 ? Math.round(100 * (m.cache_read_tokens || 0) / totalInput) : 0
  const items: [string, string | number][] = [
    ["LLM-Calls", m.llm_calls || 0],
    ["Input Tokens", formatN(m.input_tokens || 0)],
    ["Output Tokens", formatN(m.output_tokens || 0)],
    ["Cache Read", formatN(m.cache_read_tokens || 0)],
    ["Cache Creation", formatN(m.cache_creation_tokens || 0)],
    ["Cache-Hit", `${cacheRatio}%`],
    ["Kosten", formatCost(m.cost_micros || 0)],
    ["LLM-Zeit", `${formatMs(m.total_llm_ms || 0)}`],
    ["Tool-Calls", m.tool_calls || 0],
    ["Tool-Fehler", m.tool_errors || 0],
    ["Compactions", m.compactions || 0],
    ["Fehler", m.errors || 0],
  ]
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
      {items.map(([label, val]) => (
        <div key={label} className="rounded-lg border border-white/[8%] bg-white/[3%] px-3 py-2">
          <p className="text-zinc-500 text-[10px] uppercase tracking-wide truncate">{label}</p>
          <p className="text-base font-bold text-white leading-tight">{val}</p>
        </div>
      ))}
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-white/[8%] bg-white/[3%] p-3">
      <h3 className="text-[11px] font-semibold uppercase tracking-widest text-zinc-500 mb-2">{title}</h3>
      {children}
    </div>
  )
}

function LlmCallsTable({ rows }: { rows: SessionDetail["llm_calls"] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead className="text-zinc-500 text-[10px] uppercase">
          <tr>
            <Th>Iteration</Th><Th>Zeit</Th><Th>Modell</Th>
            <Th right>Input</Th><Th right>Output</Th><Th right>Cache R/C</Th>
            <Th right>Dauer</Th><Th right>Kosten</Th><Th>Stop</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t border-white/[4%] hover:bg-white/[2%]">
              <Td>{r.turn_in_session ?? "?"}</Td>
              <Td className="text-zinc-500">{shortTime(r.created_at)}</Td>
              <Td className="font-mono text-[10px]">{r.model}</Td>
              <Td right>{formatN(r.prompt_tokens || 0)}</Td>
              <Td right>{formatN(r.completion_tokens || 0)}</Td>
              <Td right className="text-zinc-500">
                {formatN(r.cache_read_tokens || 0)}/{formatN(r.cache_creation_tokens || 0)}
              </Td>
              <Td right>{formatMs(r.total_ms || 0)}</Td>
              <Td right className="text-amber-400">{formatCost(r.cost_micros || 0)}</Td>
              <Td className="text-zinc-500">{r.stop_reason}</Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ToolCallsTable({ rows }: { rows: SessionDetail["tool_calls"] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead className="text-zinc-500 text-[10px] uppercase">
          <tr>
            <Th>It.</Th><Th>Zeit</Th><Th>Tool</Th><Th>Status</Th>
            <Th right>Dauer</Th><Th right>Args</Th><Th right>Result</Th><Th>Args-Preview</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t border-white/[4%] hover:bg-white/[2%]">
              <Td>{r.iteration ?? "?"}</Td>
              <Td className="text-zinc-500">{shortTime(r.created_at)}</Td>
              <Td className="font-mono">{r.tool_name}</Td>
              <Td className={r.status === "error" ? "text-rose-400" : "text-emerald-400"}>{r.status}</Td>
              <Td right>{formatMs(r.duration_ms || 0)}</Td>
              <Td right>{formatBytes(r.arguments_size_bytes)}</Td>
              <Td right className={r.result_truncated ? "text-amber-400" : ""}>
                {formatBytes(r.result_size_bytes)}{r.result_truncated ? "✂" : ""}
              </Td>
              <Td className="text-zinc-500 text-[10px] max-w-md truncate">{r.arguments_preview}</Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CompactionsTable({ rows }: { rows: SessionDetail["compactions"] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead className="text-zinc-500 text-[10px] uppercase">
          <tr>
            <Th>Zeit</Th><Th>Trigger</Th><Th>Skip?</Th>
            <Th right>Msgs vorher</Th><Th right>Msgs gekept</Th>
            <Th right>Tokens vorher</Th><Th right>Tokens nachher</Th><Th right>Dauer</Th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t border-white/[4%]">
              <Td className="text-zinc-500">{shortTime(r.created_at)}</Td>
              <Td>{r.triggered_by} {r.trigger_threshold_pct ? `@${r.trigger_threshold_pct}%` : ""}</Td>
              <Td className={r.skipped ? "text-amber-400" : "text-emerald-400"}>
                {r.skipped ? r.skip_reason : "nein"}
              </Td>
              <Td right>{r.messages_visible_before ?? "—"}</Td>
              <Td right>{r.messages_kept ?? "—"}</Td>
              <Td right>{formatN(r.tokens_before || 0)}</Td>
              <Td right>{formatN(r.tokens_after_estimate || 0)}</Td>
              <Td right>{formatMs(r.duration_ms || 0)}</Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ErrorsTable({ rows }: { rows: SessionDetail["errors"] }) {
  return (
    <div className="space-y-1">
      {rows.map((r) => (
        <div key={r.id} className="rounded-md border border-rose-500/30 bg-rose-500/5 px-3 py-2">
          <div className="flex items-center gap-2 text-[11px]">
            <span className="font-mono text-rose-400">{r.error_type || "?"}</span>
            <span className="text-zinc-500">·</span>
            <span className="text-zinc-400">{r.source}</span>
            <span className="text-zinc-500 ml-auto">{shortTime(r.created_at)}</span>
          </div>
          <p className="text-xs text-zinc-200 mt-0.5">{r.error_message}</p>
        </div>
      ))}
    </div>
  )
}

function Th({ children, right }: { children?: React.ReactNode; right?: boolean }) {
  return <th className={`px-2 py-1 ${right ? "text-right" : "text-left"} font-normal`}>{children}</th>
}
function Td({ children, className, right }: { children?: React.ReactNode; className?: string; right?: boolean }) {
  return <td className={`px-2 py-1 ${right ? "text-right" : ""} ${className || ""}`}>{children}</td>
}

function shortTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
}
function formatN(n: number): string {
  if (n < 1000) return String(n)
  if (n < 1_000_000) return `${(n / 1000).toFixed(1)}k`
  return `${(n / 1_000_000).toFixed(2)}M`
}
function formatMs(n: number): string {
  if (n < 1000) return `${n}ms`
  if (n < 60_000) return `${(n / 1000).toFixed(1)}s`
  return `${Math.floor(n / 60_000)}m${Math.floor((n % 60_000) / 1000)}s`
}
function formatBytes(b: number | null): string {
  if (b == null) return "—"
  if (b < 1024) return `${b}B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)}kB`
  return `${(b / (1024 * 1024)).toFixed(1)}MB`
}
function formatCost(micros: number): string {
  const euro = micros / 100_000
  if (euro < 0.01) return `${(micros / 1000).toFixed(2)}¢`
  if (euro < 1) return `${(euro * 100).toFixed(1)}¢`
  return `€${euro.toFixed(2)}`
}
