import React from "react"
import {
  ReactFlow, Background, Controls, MiniMap, BackgroundVariant, Panel,
  type Connection, type Edge,
} from "@xyflow/react"
import { useTranslation } from "react-i18next"
import type { BNode } from "./types"
import { NODE_TYPES } from "./nodes"

interface Props {
  nodes: BNode[]
  edges: Edge[]
  isDark: boolean
  onNodesChange: (changes: unknown) => void
  onEdgesChange: (changes: unknown) => void
  onConnect: (c: Connection) => void
  onNodeClick: (e: React.MouseEvent, node: BNode) => void
  onPaneClick: () => void
  onDrop: (e: React.DragEvent) => void
  onDragOver: (e: React.DragEvent) => void
}

export function ButlerCanvas({
  nodes, edges, isDark,
  onNodesChange, onEdgesChange, onConnect, onNodeClick, onPaneClick,
  onDrop, onDragOver,
}: Props) {
  const { t } = useTranslation("butler")

  return (
    <div className="flex-1 relative" onDrop={onDrop} onDragOver={onDragOver}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange as never}
        onEdgesChange={onEdgesChange as never}
        onConnect={onConnect}
        onNodeClick={onNodeClick as never}
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
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="rgba(255,255,255,0.05)" />
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
  )
}
