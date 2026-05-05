import { useEffect, useMemo, useState } from "react"
import { Loader2, RefreshCw, ArrowLeft, Search, Zap, CheckCircle, XCircle, HelpCircle } from "lucide-react"
import { Link } from "react-router-dom"
import { chatApi } from "@/features/chat/api"
import type { AgentBrief } from "@/features/chat/types"
import { catalogApi, type CatalogModel, type CatalogProvider, type CatalogTestResult } from "./api"

export function CatalogPage() {
  const [providers, setProviders] = useState<CatalogProvider[]>([])
  const [activePid, setActivePid] = useState<string>("")
  const [search, setSearch] = useState("")
  const [filter, setFilter] = useState<"all" | "tool_use" | "no_tools" | "unknown">("all")
  const [loading, setLoading] = useState(true)
  const [testing, setTesting] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, CatalogTestResult>>({})
  const [agents, setAgents] = useState<AgentBrief[]>([])
  const [useDialogModel, setUseDialogModel] = useState<string | null>(null)
  const [useError, setUseError] = useState<string | null>(null)

  function load() {
    setLoading(true)
    catalogApi.get().then((r) => {
      setProviders(r.providers)
      if (!activePid && r.providers.length) setActivePid(r.providers[0].provider_id)
    }).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    chatApi.listAgents().then(setAgents).catch(() => {})
  }, [])

  const active = providers.find((p) => p.provider_id === activePid)

  const filtered = useMemo(() => {
    if (!active) return []
    let xs = active.models
    if (search) {
      const s = search.toLowerCase()
      xs = xs.filter((m) => m.id.toLowerCase().includes(s))
    }
    if (filter === "tool_use") xs = xs.filter((m) => m.tool_use === true)
    if (filter === "no_tools") xs = xs.filter((m) => m.tool_use === false)
    if (filter === "unknown") xs = xs.filter((m) => m.unknown)
    return xs
  }, [active, search, filter])

  async function runTest(model: string) {
    setTesting(model)
    try {
      const r = await catalogApi.test(model)
      setTestResults((cur) => ({ ...cur, [model]: r }))
    } finally { setTesting(null) }
  }

  async function applyToAgent(agentId: string, model: string) {
    setUseError(null)
    try {
      await catalogApi.useInAgent(agentId, model)
      setUseDialogModel(null)
      // Agent-Liste neu laden für UI
      const fresh = await chatApi.listAgents()
      setAgents(fresh)
    } catch (e) {
      setUseError(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <div className="space-y-4 max-w-6xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs text-zinc-500 mb-1">
            <Link to="/llm" className="hover:text-zinc-300 inline-flex items-center gap-1">
              <ArrowLeft size={12} /> LLM-Konfiguration
            </Link>
          </div>
          <h1 className="text-xl font-bold text-white">Modell-Catalog</h1>
          <p className="text-zinc-500 text-sm mt-0.5">
            Live-Listing pro Provider. Test-Button macht 1 Mini-Call (kostet 1 API-Credit).
          </p>
        </div>
        <button onClick={load} disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/5 disabled:opacity-50">
          {loading ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
          Aktualisieren
        </button>
      </div>

      <div className="flex flex-wrap gap-1 border-b border-white/[6%]">
        {providers.map((p) => (
          <button key={p.provider_id} onClick={() => setActivePid(p.provider_id)}
            className={`px-3 py-2 text-sm border-b-2 -mb-px transition-colors ${
              p.provider_id === activePid
                ? "border-violet-500 text-zinc-100"
                : "border-transparent text-zinc-500 hover:text-zinc-300"
            }`}>
            {p.provider_name}
            <span className="ml-1.5 text-[10px] text-zinc-600">({p.live_count})</span>
            {!p.configured && <span className="ml-1 text-[10px] text-amber-400">(kein Key)</span>}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Suche…"
            className="w-full pl-9 pr-3 py-2 rounded-lg bg-white/[3%] border border-white/[8%] text-zinc-200 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500/50" />
        </div>
        <div className="flex gap-1">
          {(["all", "tool_use", "no_tools", "unknown"] as const).map((f) => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                filter === f
                  ? "bg-violet-500/15 text-violet-200 border border-violet-500/30"
                  : "text-zinc-400 hover:bg-white/5 border border-transparent"
              }`}>
              {f === "all" ? "Alle" : f === "tool_use" ? "Mit Tools" : f === "no_tools" ? "Ohne Tools" : "Unbekannt"}
            </button>
          ))}
        </div>
        <span className="text-xs text-zinc-600 ml-auto">{filtered.length} Modelle</span>
      </div>

      <div className="rounded-xl border border-white/[8%] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-white/[3%] text-[10px] uppercase tracking-widest text-zinc-500">
            <tr>
              <th className="text-left px-3 py-2 font-semibold">Modell</th>
              <th className="text-right px-3 py-2 font-semibold">Context</th>
              <th className="text-center px-3 py-2 font-semibold">Tools</th>
              <th className="text-left px-3 py-2 font-semibold">Kategorie</th>
              <th className="text-left px-3 py-2 font-semibold">Größe</th>
              <th className="text-right px-3 py-2 font-semibold">Test</th>
              <th className="text-right px-3 py-2 font-semibold">Aktion</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((m) => <Row key={m.id} m={m} testResult={testResults[m.id]} testing={testing === m.id}
              onTest={() => runTest(m.id)} onUse={() => setUseDialogModel(m.id)} />)}
          </tbody>
        </table>
        {filtered.length === 0 && !loading && (
          <p className="px-3 py-6 text-center text-sm text-zinc-600">Keine Modelle in diesem Filter.</p>
        )}
      </div>

      {useDialogModel && (
        <UseInAgentDialog model={useDialogModel} agents={agents}
          onSubmit={(aid) => applyToAgent(aid, useDialogModel)}
          onCancel={() => { setUseDialogModel(null); setUseError(null) }}
          error={useError} />
      )}
    </div>
  )
}

function Row({
  m, testResult, testing, onTest, onUse,
}: { m: CatalogModel; testResult?: CatalogTestResult; testing: boolean; onTest: () => void; onUse: () => void }) {
  return (
    <tr className="border-t border-white/[5%] hover:bg-white/[2%]">
      <td className="px-3 py-2 font-mono text-xs text-zinc-200 break-all">{m.id}</td>
      <td className="px-3 py-2 text-right text-xs tabular-nums text-zinc-400">
        {m.context_window ? m.context_window.toLocaleString("de") : "—"}
      </td>
      <td className="px-3 py-2 text-center">
        {m.tool_use === true && <CheckCircle size={14} className="inline text-emerald-400" />}
        {m.tool_use === false && <XCircle size={14} className="inline text-rose-400" />}
        {m.tool_use === null && <HelpCircle size={14} className="inline text-zinc-600" />}
      </td>
      <td className="px-3 py-2 text-xs text-zinc-400">{m.category}</td>
      <td className="px-3 py-2 text-xs text-zinc-500">{m.params ?? "—"}</td>
      <td className="px-3 py-2 text-right">
        <button onClick={onTest} disabled={testing}
          className="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] text-zinc-400 hover:text-zinc-200 hover:bg-white/5 disabled:opacity-50">
          {testing ? <Loader2 size={11} className="animate-spin" /> : <Zap size={11} />}
          Test
        </button>
        {testResult && (
          <span className={`ml-2 text-[10px] ${testResult.ok ? "text-emerald-400" : "text-rose-400"}`}
                title={testResult.ok ? testResult.response : testResult.error}>
            {testResult.ok ? `✓ ${testResult.latency_ms}ms` : `✗ ${testResult.latency_ms}ms`}
          </span>
        )}
      </td>
      <td className="px-3 py-2 text-right">
        <button onClick={onUse}
          className="px-2 py-1 rounded text-[11px] text-violet-300 hover:text-violet-200 hover:bg-violet-500/10">
          Im Agent nutzen
        </button>
      </td>
    </tr>
  )
}

function UseInAgentDialog({
  model, agents, onSubmit, onCancel, error,
}: { model: string; agents: AgentBrief[]; onSubmit: (aid: string) => void; onCancel: () => void; error: string | null }) {
  const [pick, setPick] = useState<string>(agents[0]?.id ?? "")
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onCancel}>
      <div className="bg-zinc-950 border border-white/10 rounded-xl p-5 max-w-md w-full m-4 space-y-3" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-sm font-medium text-zinc-100">Modell auf Agent setzen</h3>
        <p className="text-xs text-zinc-400 break-all">→ <span className="font-mono">{model}</span></p>
        <div>
          <label className="block text-xs text-zinc-500 mb-1">Agent</label>
          <select value={pick} onChange={(e) => setPick(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-white/10 text-zinc-200 text-sm">
            {agents.map((a) => (
              <option key={a.id} value={a.id} className="bg-zinc-900">{a.name} · {a.type} · {a.llm_model}</option>
            ))}
          </select>
        </div>
        {error && <p className="text-xs text-rose-400">{error}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onCancel} className="px-3 py-1.5 rounded-lg text-sm text-zinc-400 hover:bg-white/5">Abbrechen</button>
          <button onClick={() => onSubmit(pick)} disabled={!pick}
            className="px-4 py-1.5 rounded-lg text-sm text-white bg-violet-600 hover:bg-violet-500 disabled:opacity-50">
            Speichern
          </button>
        </div>
      </div>
    </div>
  )
}
