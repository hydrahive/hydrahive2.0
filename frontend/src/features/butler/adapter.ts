import type { Edge, Node } from "@xyflow/react"
import { api } from "@/shared/api-client"
import type {
  BackendEdge, BackendFlow, BackendNode, ButlerFlow, ButlerNodeData,
} from "./types"

// Adapter zwischen octopos-Frontend-Shape und unserem Backend.

export function backendToFrontend(f: BackendFlow): ButlerFlow {
  return {
    id: f.flow_id,
    name: f.name,
    enabled: f.enabled,
    nodes: f.nodes.map((n) => ({
      id: n.id,
      type: `${n.type}Node`,
      position: n.position,
      data: { subtype: n.subtype, label: n.label || n.subtype, params: n.params },
    })) as Node<ButlerNodeData>[],
    edges: f.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.source_handle,
      animated: true,
      style: { stroke: e.source_handle === "false" ? "#ef4444" : "#6366f1", strokeWidth: 2 },
    })),
  }
}

export function frontendToBackend(flowId: string, p: {
  name: string; enabled: boolean
  nodes: Node<ButlerNodeData>[]; edges: Edge[]
}): Omit<BackendFlow, "owner"> {
  return {
    flow_id: flowId,
    name: p.name, enabled: p.enabled,
    scope: "user", scope_id: null,
    nodes: p.nodes.map((n) => ({
      id: n.id,
      type: (n.type ?? "actionNode").replace("Node", "") as BackendNode["type"],
      subtype: n.data.subtype,
      position: n.position,
      params: n.data.params,
      label: n.data.label || null,
    })),
    edges: p.edges.map((e) => ({
      id: e.id, source: e.source, target: e.target,
      source_handle: ((e.sourceHandle as BackendEdge["source_handle"]) || "output"),
    })),
  }
}

function slugify(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60) || "flow"
}

type SaveInput = {
  name: string; enabled: boolean
  nodes: Node<ButlerNodeData>[]; edges: Edge[]
}

export const butlerLegacyApi = {
  list: async (): Promise<ButlerFlow[]> => {
    const flows = await api.get<BackendFlow[]>("/butler/flows")
    return flows.map(backendToFrontend)
  },
  create: async (payload: SaveInput): Promise<ButlerFlow> => {
    const flow_id = `${slugify(payload.name)}-${Math.random().toString(36).slice(2, 6)}`
    const body = frontendToBackend(flow_id, payload)
    const created = await api.post<BackendFlow>("/butler/flows", body)
    return backendToFrontend(created)
  },
  update: async (id: string, payload: SaveInput): Promise<ButlerFlow> => {
    const body = frontendToBackend(id, payload)
    const updated = await api.put<BackendFlow>(`/butler/flows/${id}`, body)
    return backendToFrontend(updated)
  },
  remove: async (id: string): Promise<void> => {
    await api.delete<void>(`/butler/flows/${id}`)
  },
  toggle: async (id: string, current: ButlerFlow): Promise<{ enabled: boolean }> => {
    const body = frontendToBackend(id, {
      name: current.name, enabled: !current.enabled,
      nodes: current.nodes, edges: current.edges,
    })
    const updated = await api.put<BackendFlow>(`/butler/flows/${id}`, body)
    return { enabled: updated.enabled }
  },
}
