import "@xyflow/react/dist/style.css";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  useReactFlow,
  BackgroundVariant,
  Panel,
  type Connection,
  type Edge,
} from "@xyflow/react";
import {
  Workflow, Plus, Save, Trash2, ToggleLeft, ToggleRight,
} from "lucide-react";
import { api } from "@/shared/api-client";
import { cn } from "@/shared/cn";
import { useTranslation } from "react-i18next";

import type { BNode, ButlerFlow } from "./types";
import { butlerLegacyApi } from "./adapter";
import { defaultParams } from "./palette-data";
import { NODE_TYPES } from "./nodes";
import { NodePalette } from "./NodePalette";
import { PropertiesPanel } from "./PropertiesPanel";




// ── Main page ──────────────────────────────────────────────────────────────
export function ButlerPage() {
  return (
    <ReactFlowProvider>
      <ButlerPageInner />
    </ReactFlowProvider>
  );
}

let _nSeq = 0;
function genId(type: string) { return `${type}-${++_nSeq}-${Date.now()}`; }

function ButlerPageInner() {
  const { t } = useTranslation("butler");

  // Projekt-Kontext aus URL Query-Parameter (#566)
  const projectId = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get("project") || null;
  }, []);
  const [flows, setFlows]           = useState<ButlerFlow[]>([]);
  const [activeFlowId, setActiveId] = useState<string | null>(null);
  const [flowName, setFlowName]     = useState(() => t("newFlowName"));
  const [flowEnabled, setEnabled]   = useState(true);
  const [saving, setSaving]         = useState(false);
  const [toast, setToast]           = useState<string | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<BNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedId, setSelectedId]     = useState<string | null>(null);

  const [agents, setAgents] = useState<{ id: string; name: string }[]>([]);
  const rf = useReactFlow();

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  // Load flows + agents
  useEffect(() => {
    butlerLegacyApi.list()
      .then(setFlows)
      .catch(e => console.error("Failed to load butler flows", e));

    api.get<Array<{ id: string; name?: string; config?: { identity?: string } }>>("/agents")
      .then(res => {
        const list = (res || []).map((a) => ({
          id: a.id,
          name: a.config?.identity
            ? `${a.id} — ${String(a.config.identity).slice(0, 30)}`
            : (a.name || a.id),
        }));
        setAgents(list);
      })
      .catch(e => console.error("Failed to load agents for butler", e));
  }, []);

  const loadFlow = (flow: ButlerFlow) => {
    setActiveId(flow.id);
    setFlowName(flow.name);
    setEnabled(flow.enabled);
    setNodes((flow.nodes || []) as BNode[]);
    setEdges(flow.edges || []);
    setSelectedId(null);
  };

  const newFlow = () => {
    setActiveId(null);
    setFlowName(t("newFlowName"));
    setEnabled(true);
    setNodes([]);
    setEdges([]);
    setSelectedId(null);
  };

  const saveFlow = async () => {
    setSaving(true);
    try {
      const payload = { name: flowName, enabled: flowEnabled, nodes, edges };
      if (activeFlowId) {
        const updated = await butlerLegacyApi.update(activeFlowId, payload);
        setFlows(fs => fs.map(f => f.id === activeFlowId ? updated : f));
      } else {
        const created = await butlerLegacyApi.create(payload);
        setFlows(fs => [...fs, created]);
        setActiveId(created.id);
      }
      showToast("Gespeichert");
    } catch (e) {
      showToast(e instanceof Error ? e.message : "Speicherfehler");
    } finally {
      setSaving(false);
    }
  };

  const deleteFlow = async () => {
    if (!activeFlowId) return;
    if (!confirm(`Flow "${flowName}" wirklich löschen?`)) return;
    try {
      await butlerLegacyApi.remove(activeFlowId);
      setFlows(fs => fs.filter(f => f.id !== activeFlowId));
      newFlow();
      showToast("Gelöscht");
    } catch (e) {
      showToast(e instanceof Error ? e.message : "Fehler");
    }
  };

  const toggleFlow = async () => {
    if (!activeFlowId) { setEnabled(e => !e); return; }
    const current = flows.find(f => f.id === activeFlowId);
    if (!current) return;
    try {
      const res = await butlerLegacyApi.toggle(activeFlowId, { ...current, name: flowName, nodes, edges });
      setEnabled(res.enabled);
      setFlows(fs => fs.map(f => f.id === activeFlowId ? { ...f, enabled: res.enabled } : f));
    } catch (e) {
      showToast(e instanceof Error ? e.message : "Fehler");
    }
  };

  const onConnect = useCallback((c: Connection) => {
    setEdges(es => addEdge({
      ...c,
      animated: true,
      style: { stroke: "#6366f1", strokeWidth: 2 },
    }, es));
  }, [setEdges]);

  const onDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    const raw = event.dataTransfer.getData("application/butler-node");
    if (!raw) return;
    const { type, subtype, label } = JSON.parse(raw) as { type: string; subtype: string; label: string };
    const position = rf.screenToFlowPosition({ x: event.clientX, y: event.clientY });
    setNodes(ns => [...ns, {
      id: genId(type),
      type,
      position,
      data: { subtype, label, params: defaultParams(subtype) },
    } as BNode]);
  }, [rf, setNodes]);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  const onNodeClick = useCallback((_: React.MouseEvent, node: BNode) => {
    setSelectedId(node.id);
  }, []);

  const onPaneClick = useCallback(() => setSelectedId(null), []);

  const selectedNode = nodes.find(n => n.id === selectedId) as BNode | undefined;

  const updateParams = (params: Record<string, unknown>) => {
    if (!selectedId) return;
    setNodes(ns => ns.map(n =>
      n.id === selectedId ? { ...n, data: { ...n.data, params } } : n
    ) as BNode[]);
  };

  const deleteSelected = () => {
    if (!selectedId) return;
    setNodes(ns => (ns as BNode[]).filter(n => n.id !== selectedId));
    setEdges(es => es.filter(e => e.source !== selectedId && e.target !== selectedId));
    setSelectedId(null);
  };

  const isDark = typeof document !== "undefined" && document.documentElement.classList.contains("dark");

  return (
    <div className="flex h-full flex-col">
      {/* ── Top bar ── */}
      <div className="flex flex-wrap items-center gap-2 border-b border-white/10 px-4 py-2.5 shrink-0">
        <Workflow className="h-5 w-5 text-indigo-400 shrink-0" />
        <h1 className="text-base font-semibold text-white mr-1">Butler</h1>
        {projectId && (
          <span className="rounded-full bg-indigo-500/20 px-2.5 py-0.5 text-[11px] font-medium text-indigo-300">
            {projectId}
          </span>
        )}

        {/* Flow selector */}
        <select
          value={activeFlowId || ""}
          onChange={e => {
            const flow = flows.find(f => f.id === e.target.value);
            if (flow) loadFlow(flow); else newFlow();
          }}
          className="rounded-lg bg-zinc-900 border border-white/15 px-2.5 py-1.5 text-sm text-white focus:outline-none focus:border-indigo-500/50"
        >
          <option value="">{t("newFlowOption")}</option>
          {flows.map(f => (
            <option key={f.id} value={f.id}>{f.name}{f.enabled ? "" : ` ${t("inactive")}`}</option>
          ))}
        </select>

        {/* Name */}
        <input
          type="text"
          value={flowName}
          onChange={e => setFlowName(e.target.value)}
          placeholder={t("flowNamePlaceholder")}
          className="rounded-lg bg-zinc-900 border border-white/15 px-2.5 py-1.5 text-sm text-white placeholder-white/25 focus:outline-none focus:border-indigo-500/50 w-40"
        />

        {/* Toggle */}
        <button type="button" onClick={toggleFlow}
          className={cn(
            "flex items-center gap-1.5 text-sm px-2.5 py-1.5 rounded-lg border transition-colors",
            flowEnabled
              ? "border-green-500/40 bg-green-950/30 text-green-400 hover:bg-green-950/50"
              : "border-white/15 bg-zinc-900 text-white/35 hover:bg-white/10"
          )}
        >
          {flowEnabled ? <ToggleRight className="h-4 w-4" /> : <ToggleLeft className="h-4 w-4" />}
          {flowEnabled ? t("active") : t("inactiveLabel")}
        </button>

        <div className="flex-1" />

        <button type="button" onClick={newFlow}
          className="flex items-center gap-1.5 rounded-lg border border-white/15 bg-zinc-900 px-2.5 py-1.5 text-sm text-white hover:bg-white/10 transition-colors"
        >
          <Plus className="h-3.5 w-3.5" />
          {"Neu"}
        </button>

        <button type="button" onClick={saveFlow} disabled={saving}
          className="flex items-center gap-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 px-3 py-1.5 text-sm text-white transition-colors"
        >
          <Save className="h-3.5 w-3.5" />
          {saving ? "Speichert…" : "Speichern"}
        </button>

        {activeFlowId && (
          <button type="button" onClick={deleteFlow}
            className="flex items-center gap-1.5 rounded-lg border border-red-500/40 bg-red-950/20 px-2.5 py-1.5 text-sm text-red-400 hover:bg-red-950/40 transition-colors"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* ── Toast ── */}
      {toast && (
        <div className="px-4 py-1.5 bg-indigo-900/40 border-b border-indigo-500/30 text-sm text-indigo-200">
          {toast}
        </div>
      )}

      {/* ── Main area ── */}
      <div className="flex flex-1 overflow-hidden">
        <NodePalette />

        {/* Canvas */}
        <div className="flex-1 relative" onDrop={onDrop} onDragOver={onDragOver}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={NODE_TYPES}
            colorMode={isDark ? "dark" : "light"}
            fitView
            snapToGrid
            snapGrid={[15, 15]}
            defaultEdgeOptions={{
              animated: true,
              style: { stroke: "#6366f1", strokeWidth: 2 },
            }}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={20}
              size={1}
              color="rgba(255,255,255,0.05)"
            />
            <Controls />
            <MiniMap
              nodeColor={n =>
                n.type === "triggerNode"   ? "#22c55e" :
                n.type === "conditionNode" ? "#3b82f6" : "#f97316"
              }
            />
            {nodes.length === 0 && (
              <Panel position="top-center" style={{ marginTop: 48 }}>
                <div className="text-center pointer-events-none">
                  <p className="text-white/25 text-base">{t("canvasEmptyHint")}</p>
                  <p className="text-white/15 text-sm mt-1">{t("canvasEmptySubHint")}</p>
                </div>
              </Panel>
            )}
          </ReactFlow>
        </div>

        {/* Properties panel */}
        {selectedNode && (
          <PropertiesPanel
            node={selectedNode}
            agents={agents}
            onChange={updateParams}
            onDelete={deleteSelected}
          />
        )}
      </div>
    </div>
  );
}
