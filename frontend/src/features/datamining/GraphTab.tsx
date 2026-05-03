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
  label: string
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

const CLUSTER_COLORS = d3.schemeTableau10

export function GraphTab() {
  const svgRef = useRef<SVGSVGElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [nodeCount, setNodeCount] = useState(0)
  const [tooltip, setTooltip] = useState<{ x: number; y: number; node: GraphNode } | null>(null)
  const [limit, setLimit] = useState(1000)

  async function load() {
    setLoading(true)
    setError(null)
    setTooltip(null)
    try {
      const data = await dataminingApi.graph({ limit }) as GraphData
      if (!data.active) { setError("Mirror nicht aktiv"); return }
      if (data.error) { setError(data.error); return }
      setNodeCount(data.nodes.length)
      renderGraph(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler")
    } finally {
      setLoading(false)
    }
  }

  function renderGraph(data: GraphData) {
    const svg = svgRef.current
    if (!svg) return
    d3.select(svg).selectAll("*").remove()

    const W = svg.clientWidth || 800
    const H = svg.clientHeight || 600

    const root = d3.select(svg)
      .attr("width", W)
      .attr("height", H)

    const g = root.append("g")

    // Zoom
    root.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 10])
        .on("zoom", (e) => g.attr("transform", e.transform))
    )

    // UMAP-Koordinaten auf SVG skalieren
    const xs = d3.scaleLinear()
      .domain(d3.extent(data.nodes, (n) => n.x) as [number, number])
      .range([40, W - 40])
    const ys = d3.scaleLinear()
      .domain(d3.extent(data.nodes, (n) => n.y) as [number, number])
      .range([40, H - 40])

    const nodeById = new Map(data.nodes.map((n) => [n.id, n]))

    // Edges
    g.append("g").selectAll("line")
      .data(data.edges)
      .join("line")
      .attr("x1", (e) => xs(nodeById.get(e.source)?.x ?? 0))
      .attr("y1", (e) => ys(nodeById.get(e.source)?.y ?? 0))
      .attr("x2", (e) => xs(nodeById.get(e.target)?.x ?? 0))
      .attr("y2", (e) => ys(nodeById.get(e.target)?.y ?? 0))
      .attr("stroke", "rgba(255,255,255,0.06)")
      .attr("stroke-width", (e) => (e.weight - 0.8) * 8)

    // Nodes
    g.append("g").selectAll("circle")
      .data(data.nodes)
      .join("circle")
      .attr("cx", (n) => xs(n.x))
      .attr("cy", (n) => ys(n.y))
      .attr("r", 4)
      .attr("fill", (n) => n.cluster < 0
        ? "rgba(255,255,255,0.15)"
        : CLUSTER_COLORS[n.cluster % CLUSTER_COLORS.length])
      .attr("stroke", "none")
      .style("cursor", "pointer")
      .on("mouseenter", (event: MouseEvent, n: GraphNode) => {
        setTooltip({ x: event.clientX, y: event.clientY, node: n })
      })
      .on("mousemove", (event: MouseEvent) => {
        setTooltip((t) => t ? { ...t, x: event.clientX, y: event.clientY } : null)
      })
      .on("mouseleave", () => setTooltip(null))
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="px-2 py-1 rounded-lg text-xs bg-white/[4%] border border-white/[8%] text-zinc-300"
        >
          <option value={500}>500 Nodes</option>
          <option value={1000}>1000 Nodes</option>
          <option value={2000}>2000 Nodes</option>
          <option value={3000}>3000 Nodes</option>
        </select>
        <button
          onClick={load}
          disabled={loading}
          className="px-3 py-1.5 rounded-lg text-xs bg-violet-500/15 border border-violet-500/30 text-violet-300 hover:bg-violet-500/25 disabled:opacity-40 transition-colors"
        >
          {loading ? "berechne…" : "Graph laden"}
        </button>
        {nodeCount > 0 && !loading && (
          <span className="text-xs text-zinc-500">{nodeCount} Nodes</span>
        )}
        {error && <span className="text-xs text-rose-400">{error}</span>}
      </div>

      <div className="relative rounded-xl border border-white/[6%] bg-zinc-950 overflow-hidden" style={{ height: "calc(100dvh - 20rem)" }}>
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
      </div>

      {tooltip && (
        <div
          className="fixed z-50 pointer-events-none px-3 py-2 rounded-lg bg-zinc-900 border border-white/[10%] text-xs shadow-xl max-w-xs"
          style={{ left: tooltip.x + 12, top: tooltip.y - 10 }}
        >
          <div className="text-zinc-300 font-medium truncate">{tooltip.node.label || "—"}</div>
          <div className="text-zinc-500 mt-0.5 space-y-0.5">
            <div>{tooltip.node.event_type}</div>
            {tooltip.node.agent_name && <div>{tooltip.node.agent_name}</div>}
            <div className="text-zinc-600">Cluster {tooltip.node.cluster < 0 ? "—" : tooltip.node.cluster}</div>
          </div>
        </div>
      )}
    </div>
  )
}
