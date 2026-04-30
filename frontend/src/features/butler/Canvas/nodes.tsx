import { Handle, Position } from "@xyflow/react"
import { Bell, Filter, Zap } from "lucide-react"
import type { NodeType } from "../types"

interface NodeData {
  subtype: string
  label?: string | null
  summary?: string
}

const STYLES: Record<NodeType, { ring: string; bg: string; icon: React.ReactNode; text: string }> = {
  trigger: { ring: "border-emerald-500/50", bg: "bg-emerald-500/10", text: "text-emerald-200",
             icon: <Bell size={11} className="text-emerald-300" /> },
  condition: { ring: "border-sky-500/50", bg: "bg-sky-500/10", text: "text-sky-200",
               icon: <Filter size={11} className="text-sky-300" /> },
  action: { ring: "border-amber-500/50", bg: "bg-amber-500/10", text: "text-amber-200",
            icon: <Zap size={11} className="text-amber-300" /> },
}

function NodeShell({ data, type }: { data: NodeData; type: NodeType }) {
  const s = STYLES[type]
  return (
    <div className={`min-w-[170px] rounded-lg border-2 ${s.ring} ${s.bg} px-3 py-2 shadow-md`}>
      <div className="flex items-center gap-1.5">
        {s.icon}
        <span className={`text-[10px] uppercase tracking-wider ${s.text}`}>{type}</span>
      </div>
      <p className="text-xs font-semibold text-zinc-100 mt-0.5">
        {data.label || data.subtype}
      </p>
      {data.summary && (
        <p className="text-[10px] text-zinc-400 mt-0.5 truncate max-w-[200px]">{data.summary}</p>
      )}
    </div>
  )
}

export function TriggerNode({ data }: { data: NodeData }) {
  return (
    <>
      <NodeShell data={data} type="trigger" />
      <Handle type="source" position={Position.Right} id="output"
        className="!bg-emerald-400 !border-emerald-600" />
    </>
  )
}

export function ConditionNode({ data }: { data: NodeData }) {
  return (
    <>
      <Handle type="target" position={Position.Left}
        className="!bg-zinc-500 !border-zinc-700" />
      <NodeShell data={data} type="condition" />
      <Handle type="source" position={Position.Right} id="true" style={{ top: "35%" }}
        className="!bg-emerald-400 !border-emerald-600" />
      <Handle type="source" position={Position.Right} id="false" style={{ top: "70%" }}
        className="!bg-rose-400 !border-rose-600" />
    </>
  )
}

export function ActionNode({ data }: { data: NodeData }) {
  return (
    <>
      <Handle type="target" position={Position.Left}
        className="!bg-zinc-500 !border-zinc-700" />
      <NodeShell data={data} type="action" />
      <Handle type="source" position={Position.Right} id="output"
        className="!bg-amber-400 !border-amber-600" />
    </>
  )
}

export const NODE_TYPES = {
  trigger: TriggerNode,
  condition: ConditionNode,
  action: ActionNode,
}
