import React, { useCallback, useEffect, useState } from "react"
import { dataminingApi } from "./api"

const ForceGraph3D = React.lazy(() => import("react-force-graph-3d"))

interface GraphNode {
  id: string
  label: string
  type: "agent" | "user" | "tool"
  group: string
  val: number
  session_count?: number
  use_count?: number
  x?: number; y?: number; z?: number
}

interface GraphLink {
  source: string | GraphNode
  target: string | GraphNode
  type: string
  value: number
}

interface TopologyData {
  active: boolean
  nodes: GraphNode[]
  links: GraphLink[]
  active_agents: string[]
  error?: string
}

const GROUP_COLORS: Record<string, string> = {
  agent: "#22d3ee",
  user:  "#a78bfa",
  tool:  "#fb923c",
}

const GROUP_LABELS: Record<string, string> = {
  agent: "Agent", user: "User", tool: "Tool",
}

export function GraphTab() {
  const [data, setData] = useState<TopologyData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<GraphNode | null>(null)
  const [activeAgents, setActiveAgents] = useState<Set<string>>(new Set())

  async function load() {
    setLoading(true); setError(null); setSelected(null)
    try {
      const d = await dataminingApi.graph() as TopologyData
      if (!d.active) { setError("Mirror nicht aktiv"); return }
      if (d.error) { setError(d.error); return }
      setData(d)
      setActiveAgents(new Set(d.active_agents))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!data) return
    const iv = setInterval(async () => {
      try {
        const d = await dataminingApi.graph() as TopologyData
        if (d.active_agents) setActiveAgents(new Set(d.active_agents))
      } catch {}
    }, 10000)
    return () => clearInterval(iv)
  }, [!!data])

  const nodeColor = useCallback((n: unknown) => {
    const node = n as GraphNode
    if (node.group === "agent" && activeAgents.has(node.label)) return "#ffffff"
    return GROUP_COLORS[node.group] ?? "#94a3b8"
  }, [activeAgents])

  const nodeVal = useCallback((n: unknown) => {
    const node = n as GraphNode
    if (node.group === "agent" && activeAgents.has(node.label)) return node.val * 1.8
    return node.val
  }, [activeAgents])

  const handleNodeClick = useCallback((n: unknown) => setSelected(n as GraphNode), [])

  const connections = selected && data ? data.links.filter(l => {
    const src = typeof l.source === "object" ? (l.source as GraphNode).id : l.source
    const tgt = typeof l.target === "object" ? (l.target as GraphNode).id : l.target
    return src === selected.id || tgt === selected.id
  }) : []

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <button onClick={load} disabled={loading}
          className="px-3 py-1.5 rounded-lg text-xs bg-violet-500/15 border border-violet-500/30 text-violet-300 hover:bg-violet-500/25 disabled:opacity-40 transition-colors">
          {loading ? "lade…" : "Graph laden"}
        </button>
        {data && (
          <span className="text-xs text-zinc-500">
            {data.nodes.length} Knoten · {data.links.length} Verbindungen
          </span>
        )}
        {data && (
          <div className="flex gap-3 ml-auto">
            {Object.entries(GROUP_COLORS).map(([g, c]) => (
              <span key={g} className="flex items-center gap-1.5 text-[11px] text-zinc-400">
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: c }} />
                {GROUP_LABELS[g]}
              </span>
            ))}
            <span className="flex items-center gap-1.5 text-[11px] text-zinc-400">
              <span className="w-2 h-2 rounded-full flex-shrink-0 bg-white" />
              aktiv
            </span>
          </div>
        )}
        {error && <span className="text-xs text-rose-400">{error}</span>}
      </div>

      <div className="relative rounded-xl border border-white/[6%] bg-zinc-950 overflow-hidden"
        style={{ height: "calc(100dvh - 20rem)" }}>

        {!data && !loading && (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-zinc-600">
            Graph laden um Systemtopologie zu sehen
          </div>
        )}
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {data && (
          <React.Suspense fallback={null}>
            <ForceGraph3D
              graphData={data as never}
              nodeId="id"
              nodeLabel="label"
              nodeColor={nodeColor}
              nodeVal={nodeVal}
              linkColor={() => "rgba(255,255,255,0.12)"}
              linkWidth={(l: unknown) => Math.log(((l as GraphLink).value ?? 1) + 1) * 0.4}
              backgroundColor="#09090b"
              onNodeClick={handleNodeClick}
              d3AlphaDecay={0.03}
              d3VelocityDecay={0.5}
              warmupTicks={80}
              cooldownTicks={150}
            />
          </React.Suspense>
        )}

        {selected && (
          <div className="absolute right-0 top-0 bottom-0 w-60 bg-zinc-900/95 border-l border-white/[8%] p-4 overflow-y-auto">
            <div className="flex items-start gap-2 mb-3">
              <span className="w-3 h-3 rounded-full flex-shrink-0 mt-0.5"
                style={{ background: GROUP_COLORS[selected.group] ?? "#94a3b8" }} />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-zinc-100 break-all">{selected.label}</div>
                <div className="text-[11px] text-zinc-500 mt-0.5">{GROUP_LABELS[selected.group]}</div>
              </div>
              <button onClick={() => setSelected(null)}
                className="text-zinc-600 hover:text-zinc-300 flex-shrink-0 text-lg leading-none">×</button>
            </div>

            <div className="text-xs text-zinc-500 space-y-1 mb-4">
              {selected.session_count !== undefined && (
                <div>{selected.session_count} {selected.group === "user" ? "Sessions" : "Sessions mit Usern"}</div>
              )}
              {selected.use_count !== undefined && (
                <div>{selected.use_count}× genutzt</div>
              )}
              {activeAgents.has(selected.label) && (
                <div className="text-emerald-400 font-medium">● aktiv gerade</div>
              )}
            </div>

            {connections.length > 0 && (
              <div>
                <div className="text-[10px] text-zinc-600 uppercase tracking-wider mb-2">Verbindungen</div>
                <div className="space-y-1.5">
                  {connections.slice(0, 15).map((l, i) => {
                    const src = typeof l.source === "object" ? (l.source as GraphNode).id : l.source
                    const tgt = typeof l.target === "object" ? (l.target as GraphNode).id : l.target
                    const other = src === selected.id ? tgt : src
                    const arrow = src === selected.id ? "→" : "←"
                    const [type, name] = other.split(":")
                    return (
                      <div key={i} className="flex items-center gap-1.5 text-[11px]">
                        <span className="text-zinc-600">{arrow}</span>
                        <span className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                          style={{ background: GROUP_COLORS[type] ?? "#94a3b8" }} />
                        <span className="text-zinc-400 truncate">{name}</span>
                        <span className="text-zinc-600 ml-auto flex-shrink-0">{l.value}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
