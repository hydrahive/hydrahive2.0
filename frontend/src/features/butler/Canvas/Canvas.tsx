import { useCallback, useMemo } from "react"
import {
  Background, Controls, MiniMap, ReactFlow,
  type Connection, type Edge as RfEdge, type Node as RfNode,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { useFlowStore } from "../useFlowStore"
import { useRegistry, findSpec } from "../useRegistry"
import type { ButlerNode, NodeType, SourceHandle } from "../types"
import { NODE_TYPES } from "./nodes"

function summarize(params: Record<string, unknown>): string {
  const entries = Object.entries(params).slice(0, 2)
    .map(([k, v]) => `${k}: ${String(v).slice(0, 20)}`)
  return entries.join(" · ")
}

function newId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 8)}`
}

export function Canvas() {
  const flow = useFlowStore((s) => s.flow)
  const setNodes = useFlowStore((s) => s.setNodes)
  const setEdges = useFlowStore((s) => s.setEdges)
  const upsertNode = useFlowStore((s) => s.upsertNode)
  const select = useFlowStore((s) => s.select)
  const { registry } = useRegistry()

  const rfNodes: RfNode[] = useMemo(() => {
    if (!flow) return []
    return flow.nodes.map((n) => {
      const spec = findSpec(registry, n.type, n.subtype)
      return {
        id: n.id, type: n.type, position: n.position,
        data: {
          subtype: n.subtype,
          label: n.label || spec?.label || n.subtype,
          summary: summarize(n.params),
        },
      }
    })
  }, [flow, registry])

  const rfEdges: RfEdge[] = useMemo(() => {
    if (!flow) return []
    return flow.edges.map((e) => ({
      id: e.id, source: e.source, target: e.target,
      sourceHandle: e.source_handle,
      style: { stroke: e.source_handle === "false" ? "#fb7185" : "#34d399", strokeWidth: 2 },
    }))
  }, [flow])

  const onNodesChange = useCallback((changes: { id: string; type: string; position?: { x: number; y: number }; dragging?: boolean }[]) => {
    if (!flow) return
    const next = flow.nodes.map((n) => {
      const c = changes.find((c) => c.id === n.id && c.type === "position" && c.position)
      return c?.position ? { ...n, position: c.position } : n
    })
    setNodes(next)
    const removed = changes.filter((c) => c.type === "remove").map((c) => c.id)
    if (removed.length > 0) {
      setNodes(next.filter((n) => !removed.includes(n.id)))
    }
  }, [flow, setNodes])

  const onEdgesChange = useCallback((changes: { id: string; type: string }[]) => {
    if (!flow) return
    const removed = changes.filter((c) => c.type === "remove").map((c) => c.id)
    if (removed.length > 0) {
      setEdges(flow.edges.filter((e) => !removed.includes(e.id)))
    }
  }, [flow, setEdges])

  const onConnect = useCallback((c: Connection) => {
    if (!flow || !c.source || !c.target) return
    const handle = (c.sourceHandle as SourceHandle) || "output"
    setEdges([
      ...flow.edges.filter((e) => !(e.source === c.source && e.source_handle === handle)),
      { id: newId("e"), source: c.source, target: c.target, source_handle: handle },
    ])
  }, [flow, setEdges])

  const onDrop = useCallback((ev: React.DragEvent) => {
    ev.preventDefault()
    if (!flow) return
    const raw = ev.dataTransfer.getData("application/butler-spec")
    if (!raw) return
    const { type, subtype } = JSON.parse(raw) as { type: NodeType; subtype: string }
    if (type === "trigger" && flow.nodes.some((n) => n.type === "trigger")) {
      alert("Es darf nur einen Trigger pro Flow geben.")
      return
    }
    const bounds = ev.currentTarget.getBoundingClientRect()
    const node: ButlerNode = {
      id: newId(type), type, subtype,
      position: { x: ev.clientX - bounds.left - 80, y: ev.clientY - bounds.top - 20 },
      params: {}, label: null,
    }
    upsertNode(node)
  }, [flow, upsertNode])

  const onDragOver = useCallback((ev: React.DragEvent) => {
    ev.preventDefault()
    ev.dataTransfer.dropEffect = "move"
  }, [])

  if (!flow) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-zinc-500">
        Flow auswählen oder neuen anlegen.
      </div>
    )
  }

  return (
    <div className="h-full" onDrop={onDrop} onDragOver={onDragOver}>
      <ReactFlow
        nodes={rfNodes} edges={rfEdges}
        nodeTypes={NODE_TYPES}
        onNodesChange={onNodesChange as never}
        onEdgesChange={onEdgesChange as never}
        onConnect={onConnect}
        onNodeClick={(_, n) => select(n.id)}
        onPaneClick={() => select(null)}
        snapToGrid snapGrid={[15, 15]}
        fitView
      >
        <Background gap={15} color="#27272a" />
        <Controls className="!bg-zinc-900 !border-white/[10%]" />
        <MiniMap pannable zoomable className="!bg-zinc-900" />
      </ReactFlow>
    </div>
  )
}
