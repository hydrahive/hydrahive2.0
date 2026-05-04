import { useRef, useState } from "react"
import * as d3 from "d3"
import { dataminingApi } from "./api"

interface GraphNode {
  id: string
  x: number
  y: number
  cluster: number
  event_type: string
  agent_name: string
  username: string
  tool_name: string
  text_excerpt: string
  created_at: string
}

interface GraphEdge {
  source: string
  target: string
  weight: number
}

interface GraphData {
  active: boolean
  nodes: GraphNode[]
  edges: GraphEdge[]
  error?: string
}

type ColorBy = "cluster" | "event_type" | "agent"

const CLUSTER_COLORS = d3.schemeTableau10
const EVENT_TYPE_COLORS: Record<string, string> = {
  text: "#60a5fa",
  tool_use: "#f59e0b",
  tool_result: "#34d399",
  compaction: "#a78bfa",
  system: "#f87171",
}

function eventColor(et: string) {
  return EVENT_TYPE_COLORS[et] ?? "#94a3b8"
}


export function GraphTab() {
  const svgRef = useRef<SVGSVGElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [nodeCount, setNodeCount] = useState(0)
  const [clusterCount, setClusterCount] = useState(0)
  const [tooltip, setTooltip] = useState<{ x: number; y: number; node: GraphNode } | null>(null)
  const [limit, setLimit] = useState(1000)
  const [colorBy, setColorBy] = useState<ColorBy>("cluster")
  const dataRef = useRef<GraphData | null>(null)

  function getColor(n: GraphNode, by: ColorBy): string {
    if (by === "event_type") return eventColor(n.event_type)
    if (by === "agent") {
      const agents = dataRef.current?.nodes.map((x) => x.agent_name).filter(Boolean) ?? []
      const unique = [...new Set(agents)]
      const idx = unique.indexOf(n.agent_name)
      return idx < 0 ? "#94a3b8" : CLUSTER_COLORS[idx % CLUSTER_COLORS.length]
    }
    return n.cluster < 0 ? "rgba(255,255,255,0.08)" : CLUSTER_COLORS[n.cluster % CLUSTER_COLORS.length]
  }

  async function load() {
    setLoading(true)
    setError(null)
    setTooltip(null)
    try {
      const data = await dataminingApi.graph({ limit }) as GraphData
      if (data.error) { setError(data.error); return }
      if (!data.active) { setError("Mirror nicht aktiv"); return }
      dataRef.current = data
      setNodeCount(data.nodes.length)
      const clusters = new Set(data.nodes.map((n) => n.cluster).filter((c) => c >= 0))
      setClusterCount(clusters.size)
      renderGraph(data, colorBy)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler")
    } finally {
      setLoading(false)
    }
  }

  function recolor(by: ColorBy) {
    setColorBy(by)
    if (dataRef.current) renderGraph(dataRef.current, by)
  }

  function renderGraph(data: GraphData, by: ColorBy) {
    const svg = svgRef.current
    if (!svg) return
    d3.select(svg).selectAll("*").remove()

    const W = svg.clientWidth || 800
    const H = svg.clientHeight || 600
    const root = d3.select(svg).attr("width", W).attr("height", H)
    const g = root.append("g")

    root.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 20])
        .on("zoom", (e) => g.attr("transform", e.transform))
    )

    const xs = d3.scaleLinear()
      .domain(d3.extent(data.nodes, (n) => n.x) as [number, number])
      .range([40, W - 40])
    const ys = d3.scaleLinear()
      .domain(d3.extent(data.nodes, (n) => n.y) as [number, number])
      .range([40, H - 40])

    const nodeById = new Map(data.nodes.map((n) => [n.id, n]))

    g.append("g").selectAll("line")
      .data(data.edges)
      .join("line")
      .attr("x1", (e) => xs(nodeById.get(e.source)?.x ?? 0))
      .attr("y1", (e) => ys(nodeById.get(e.source)?.y ?? 0))
      .attr("x2", (e) => xs(nodeById.get(e.target)?.x ?? 0))
      .attr("y2", (e) => ys(nodeById.get(e.target)?.y ?? 0))
      .attr("stroke", "rgba(255,255,255,0.05)")
      .attr("stroke-width", (e) => (e.weight - 0.8) * 8)

    g.append("g").selectAll("circle")
      .data(data.nodes)
      .join("circle")
      .attr("cx", (n) => xs(n.x))
      .attr("cy", (n) => ys(n.y))
      .attr("r", (n) => n.cluster < 0 && by === "cluster" ? 2 : 4)
      .attr("fill", (n) => getColor(n, by))
      .attr("opacity", (n) => n.cluster < 0 && by === "cluster" ? 0.3 : 0.85)
      .attr("stroke", "none")
      .style("cursor", "pointer")
      .on("mouseenter", (event: MouseEvent, n: GraphNode) =>
        setTooltip({ x: event.clientX, y: event.clientY, node: n }))
      .on("mousemove", (event: MouseEvent) =>
        setTooltip((t) => t ? { ...t, x: event.clientX, y: event.clientY } : null))
      .on("mouseleave", () => setTooltip(null))
  }

  const date = tooltip?.node.created_at
    ? new Date(tooltip.node.created_at).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "2-digit", hour: "2-digit", minute: "2-digit" })
    : null

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}
          className="px-2 py-1 rounded-lg text-xs bg-white/[4%] border border-white/[8%] text-zinc-300">
          <option value={500}>500</option>
          <option value={1000}>1000</option>
          <option value={2000}>2000</option>
          <option value={3000}>3000</option>
        </select>
        <button onClick={load} disabled={loading}
          className="px-3 py-1.5 rounded-lg text-xs bg-violet-500/15 border border-violet-500/30 text-violet-300 hover:bg-violet-500/25 disabled:opacity-40 transition-colors">
          {loading ? "berechne…" : "Graph laden"}
        </button>
        {nodeCount > 0 && (
          <>
            <span className="text-xs text-zinc-500">{nodeCount} Nodes · {clusterCount} Cluster</span>
            <div className="flex gap-1 ml-2">
              {(["cluster", "event_type", "agent"] as ColorBy[]).map((by) => (
                <button key={by} onClick={() => recolor(by)}
                  className={`px-2 py-0.5 rounded text-[11px] border transition-colors ${colorBy === by ? "text-amber-300 border-amber-500/40 bg-amber-500/10" : "text-zinc-500 border-white/[6%] hover:text-zinc-300"}`}>
                  {by === "cluster" ? "Cluster" : by === "event_type" ? "Typ" : "Agent"}
                </button>
              ))}
            </div>
          </>
        )}
        {error && <span className="text-xs text-rose-400">{error}</span>}
      </div>

      <div className="relative rounded-xl border border-white/[6%] bg-zinc-950 overflow-hidden"
        style={{ height: "calc(100dvh - 20rem)" }}>
        {!nodeCount && !loading && (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-zinc-600">
            Graph laden um Embeddings zu visualisieren
          </div>
        )}
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="space-y-2 text-center">
              <div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-zinc-500">UMAP + Clustering läuft…</p>
            </div>
          </div>
        )}
        <svg ref={svgRef} className="w-full h-full" />

        {/* Event-Typ Legende */}
        {nodeCount > 0 && colorBy === "event_type" && (
          <div className="absolute bottom-3 left-3 flex flex-col gap-1 bg-zinc-950/80 px-2 py-1.5 rounded-lg border border-white/[6%]">
            {Object.entries(EVENT_TYPE_COLORS).map(([et, col]) => (
              <div key={et} className="flex items-center gap-1.5 text-[10px] text-zinc-400">
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: col }} />
                {et}
              </div>
            ))}
          </div>
        )}
      </div>

      {tooltip && (
        <div className="fixed z-50 pointer-events-none px-3 py-2 rounded-lg bg-zinc-900 border border-white/[10%] text-xs shadow-xl max-w-xs"
          style={{ left: tooltip.x + 14, top: tooltip.y - 10 }}>
          <div className="flex items-center gap-1.5 mb-1">
            <span className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ background: eventColor(tooltip.node.event_type) }} />
            <span className="text-zinc-200 font-medium">{tooltip.node.event_type}</span>
            {tooltip.node.tool_name && (
              <span className="text-zinc-500">· {tooltip.node.tool_name}</span>
            )}
          </div>
          {tooltip.node.text_excerpt && (
            <div className="text-zinc-400 mb-1 line-clamp-2">{tooltip.node.text_excerpt}</div>
          )}
          <div className="text-zinc-600 space-y-0.5">
            {tooltip.node.agent_name && <div>Agent: {tooltip.node.agent_name}</div>}
            {tooltip.node.username && <div>User: {tooltip.node.username}</div>}
            {date && <div>{date}</div>}
            {tooltip.node.cluster >= 0 && <div>Cluster {tooltip.node.cluster}</div>}
          </div>
        </div>
      )}
    </div>
  )
}
