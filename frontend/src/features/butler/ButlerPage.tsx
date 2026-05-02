import "@xyflow/react/dist/style.css"
import { ReactFlowProvider } from "@xyflow/react"
import { NodePalette } from "./NodePalette"
import { PropertiesPanel } from "./PropertiesPanel"
import { ButlerTopBar } from "./_ButlerTopBar"
import { ButlerCanvas } from "./_ButlerCanvas"
import { useButlerFlow } from "./useButlerFlow"

export function ButlerPage() {
  return (
    <ReactFlowProvider>
      <ButlerPageInner />
    </ReactFlowProvider>
  )
}

function ButlerPageInner() {
  const {
    flows, activeFlowId, flowName, flowEnabled, saving, toast, projectId,
    nodes, edges, onNodesChange, onEdgesChange,
    selectedNode, agents,
    loadFlow, newFlow, saveFlow, deleteFlow, toggleFlow,
    onConnect, onDrop, onDragOver, onNodeClick, onPaneClick,
    updateParams, deleteSelected, setFlowName,
  } = useButlerFlow()

  const isDark = typeof document !== "undefined" && document.documentElement.classList.contains("dark")

  return (
    <div className="flex h-full flex-col">
      <ButlerTopBar
        flows={flows} activeFlowId={activeFlowId} projectId={projectId}
        flowName={flowName} flowEnabled={flowEnabled} saving={saving}
        onSelectFlow={f => f ? loadFlow(f) : newFlow()}
        onNameChange={setFlowName} onToggle={toggleFlow}
        onNew={newFlow} onSave={saveFlow} onDelete={deleteFlow}
      />
      {toast && (
        <div className="px-4 py-1.5 bg-indigo-900/40 border-b border-indigo-500/30 text-sm text-indigo-200">
          {toast}
        </div>
      )}
      <div className="flex flex-1 overflow-hidden">
        <NodePalette />
        <ButlerCanvas
          nodes={nodes} edges={edges} isDark={isDark}
          onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
          onConnect={onConnect} onNodeClick={onNodeClick} onPaneClick={onPaneClick}
          onDrop={onDrop} onDragOver={onDragOver}
        />
        {selectedNode && (
          <PropertiesPanel node={selectedNode} agents={agents} onChange={updateParams} onDelete={deleteSelected} />
        )}
      </div>
    </div>
  )
}
