import { create } from "zustand"
import type { ButlerEdge, ButlerNode, Flow } from "./types"

interface FlowStore {
  flow: Flow | null
  selectedNodeId: string | null
  dirty: boolean
  setFlow: (f: Flow | null) => void
  setNodes: (nodes: ButlerNode[]) => void
  setEdges: (edges: ButlerEdge[]) => void
  upsertNode: (node: ButlerNode) => void
  removeNode: (id: string) => void
  patchNode: (id: string, patch: Partial<ButlerNode>) => void
  patchParams: (id: string, params: Record<string, unknown>) => void
  patchMeta: (m: Partial<Pick<Flow, "name" | "enabled">>) => void
  select: (id: string | null) => void
  markClean: () => void
}

export const useFlowStore = create<FlowStore>((set) => ({
  flow: null,
  selectedNodeId: null,
  dirty: false,
  setFlow: (flow) => set({ flow, dirty: false, selectedNodeId: null }),
  setNodes: (nodes) => set((s) => ({
    flow: s.flow ? { ...s.flow, nodes } : null, dirty: true,
  })),
  setEdges: (edges) => set((s) => ({
    flow: s.flow ? { ...s.flow, edges } : null, dirty: true,
  })),
  upsertNode: (node) => set((s) => {
    if (!s.flow) return s
    const others = s.flow.nodes.filter((n) => n.id !== node.id)
    return { flow: { ...s.flow, nodes: [...others, node] }, dirty: true }
  }),
  removeNode: (id) => set((s) => {
    if (!s.flow) return s
    return {
      flow: {
        ...s.flow,
        nodes: s.flow.nodes.filter((n) => n.id !== id),
        edges: s.flow.edges.filter((e) => e.source !== id && e.target !== id),
      },
      dirty: true,
      selectedNodeId: s.selectedNodeId === id ? null : s.selectedNodeId,
    }
  }),
  patchNode: (id, patch) => set((s) => {
    if (!s.flow) return s
    return {
      flow: {
        ...s.flow,
        nodes: s.flow.nodes.map((n) => n.id === id ? { ...n, ...patch } : n),
      },
      dirty: true,
    }
  }),
  patchParams: (id, params) => set((s) => {
    if (!s.flow) return s
    return {
      flow: {
        ...s.flow,
        nodes: s.flow.nodes.map((n) =>
          n.id === id ? { ...n, params: { ...n.params, ...params } } : n),
      },
      dirty: true,
    }
  }),
  patchMeta: (m) => set((s) => ({
    flow: s.flow ? { ...s.flow, ...m } : null, dirty: true,
  })),
  select: (id) => set({ selectedNodeId: id }),
  markClean: () => set({ dirty: false }),
}))
