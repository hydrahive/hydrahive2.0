import React, { useCallback, useEffect, useMemo, useState } from "react"
import { addEdge, useEdgesState, useNodesState, useReactFlow, type Connection, type Edge } from "@xyflow/react"
import { api } from "@/shared/api-client"
import { useTranslation } from "react-i18next"
import { butlerLegacyApi } from "./adapter"
import { defaultParams } from "./palette-data"
import type { BNode, ButlerFlow } from "./types"

let _nSeq = 0
export function genId(type: string) { return `${type}-${++_nSeq}-${Date.now()}` }

export function useButlerFlow() {
  const { t } = useTranslation("butler")

  const projectId = useMemo(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get("project") || null
  }, [])

  const [flows, setFlows] = useState<ButlerFlow[]>([])
  const [activeFlowId, setActiveId] = useState<string | null>(null)
  const [flowName, setFlowName] = useState(() => t("newFlowName"))
  const [flowEnabled, setEnabled] = useState(true)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  const [nodes, setNodes, onNodesChange] = useNodesState<BNode>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [agents, setAgents] = useState<{ id: string; name: string }[]>([])
  const rf = useReactFlow()

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 3000) }

  useEffect(() => {
    butlerLegacyApi.list().then(setFlows).catch(e => console.error("Failed to load butler flows", e))
    api.get<Array<{ id: string; name?: string; config?: { identity?: string } }>>("/agents")
      .then(res => setAgents((res || []).map(a => ({
        id: a.id,
        name: a.config?.identity
          ? `${a.id} — ${String(a.config.identity).slice(0, 30)}`
          : (a.name || a.id),
      }))))
      .catch(e => console.error("Failed to load agents for butler", e))
  }, [])

  const loadFlow = (flow: ButlerFlow) => {
    setActiveId(flow.id); setFlowName(flow.name); setEnabled(flow.enabled)
    setNodes((flow.nodes || []) as BNode[]); setEdges(flow.edges || []); setSelectedId(null)
  }

  const newFlow = () => {
    setActiveId(null); setFlowName(t("newFlowName")); setEnabled(true)
    setNodes([]); setEdges([]); setSelectedId(null)
  }

  const saveFlow = async () => {
    setSaving(true)
    try {
      const scope = (projectId && !activeFlowId) ? "project" as const : "user" as const
      const scope_id = (projectId && !activeFlowId) ? projectId : null
      const payload = { name: flowName, enabled: flowEnabled, nodes, edges, scope, scope_id }
      if (activeFlowId) {
        const updated = await butlerLegacyApi.update(activeFlowId, payload)
        setFlows(fs => fs.map(f => f.id === activeFlowId ? updated : f))
      } else {
        const created = await butlerLegacyApi.create(payload)
        setFlows(fs => [...fs, created]); setActiveId(created.id)
      }
      showToast("Gespeichert")
    } catch (e) {
      showToast(e instanceof Error ? e.message : "Speicherfehler")
    } finally { setSaving(false) }
  }

  const deleteFlow = async () => {
    if (!activeFlowId || !confirm(`Flow "${flowName}" wirklich löschen?`)) return
    try {
      await butlerLegacyApi.remove(activeFlowId)
      setFlows(fs => fs.filter(f => f.id !== activeFlowId)); newFlow(); showToast("Gelöscht")
    } catch (e) { showToast(e instanceof Error ? e.message : "Fehler") }
  }

  const toggleFlow = async () => {
    if (!activeFlowId) { setEnabled(e => !e); return }
    const current = flows.find(f => f.id === activeFlowId)
    if (!current) return
    try {
      const res = await butlerLegacyApi.toggle(activeFlowId, { ...current, name: flowName, nodes, edges })
      setEnabled(res.enabled)
      setFlows(fs => fs.map(f => f.id === activeFlowId ? { ...f, enabled: res.enabled } : f))
    } catch (e) { showToast(e instanceof Error ? e.message : "Fehler") }
  }

  const onConnect = useCallback((c: Connection) => {
    setEdges(es => addEdge({ ...c, animated: true, style: { stroke: "#6366f1", strokeWidth: 2 } }, es))
  }, [setEdges])

  const onDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    const raw = event.dataTransfer.getData("application/butler-node")
    if (!raw) return
    const { type, subtype, label } = JSON.parse(raw) as { type: string; subtype: string; label: string }
    const position = rf.screenToFlowPosition({ x: event.clientX, y: event.clientY })
    setNodes(ns => [...ns, { id: genId(type), type, position, data: { subtype, label, params: defaultParams(subtype) } } as BNode])
  }, [rf, setNodes])

  const onDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = "move" }, [])
  const onNodeClick = useCallback((_: React.MouseEvent, node: BNode) => { setSelectedId(node.id) }, [])
  const onPaneClick = useCallback(() => setSelectedId(null), [])

  const selectedNode = nodes.find(n => n.id === selectedId) as BNode | undefined

  const updateParams = (params: Record<string, unknown>) => {
    if (!selectedId) return
    setNodes(ns => ns.map(n => n.id === selectedId ? { ...n, data: { ...n.data, params } } : n) as BNode[])
  }

  const deleteSelected = () => {
    if (!selectedId) return
    setNodes(ns => (ns as BNode[]).filter(n => n.id !== selectedId))
    setEdges(es => es.filter(e => e.source !== selectedId && e.target !== selectedId))
    setSelectedId(null)
  }

  return {
    flows, activeFlowId, flowName, flowEnabled, saving, toast, projectId,
    nodes, edges, onNodesChange, onEdgesChange,
    selectedNode, agents,
    loadFlow, newFlow, saveFlow, deleteFlow, toggleFlow,
    onConnect, onDrop, onDragOver, onNodeClick, onPaneClick,
    updateParams, deleteSelected, setFlowName,
  }
}
