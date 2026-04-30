/**
 * Custom-Node-Komponenten für ReactFlow — Trigger / Condition / Action.
 * Werden via NODE_TYPES-Map an <ReactFlow> übergeben. Jeder Node-Typ hat
 * eigene Handles (Trigger: nur Output, Condition: 1 Input + 2 Outputs
 * für true/false, Action: Input + Output) und eigene Farben.
 */
import { Handle, Position, type NodeTypes } from "@xyflow/react"
import { Zap } from "lucide-react"
import { useTranslation } from "react-i18next"
import { cn } from "@/shared/cn"
import type { ButlerNodeData } from "./types"
import { paramSummary } from "./paramSummary"

interface NodeProps {
  data: ButlerNodeData
  selected: boolean
}

export function TriggerNodeComp({ data, selected }: NodeProps) {
  const { t } = useTranslation("butler")
  const summary = paramSummary(data.subtype, data.params, t)
  return (
    <div className={cn(
      "min-w-[185px] rounded-xl border-2 px-3 py-2.5 shadow-lg select-none",
      "border-green-500/60 bg-green-950/50",
      selected && "ring-2 ring-white/25",
    )}>
      <div className="flex items-center gap-1.5 mb-1">
        <Zap className="h-3 w-3 text-green-400" />
        <span className="text-[0.55rem] font-bold uppercase tracking-widest text-green-400">{t("groupTrigger")}</span>
      </div>
      <p className="text-sm font-medium text-white leading-tight">{data.label}</p>
      {summary && <p className="text-xs text-green-300/60 mt-0.5">{summary}</p>}
      <Handle type="source" position={Position.Right} id="output"
        style={{ background: "#22c55e", border: "2px solid #16a34a", width: 10, height: 10 }} />
    </div>
  )
}

export function ConditionNodeComp({ data, selected }: NodeProps) {
  const { t } = useTranslation("butler")
  const summary = paramSummary(data.subtype, data.params, t)
  return (
    <div className={cn(
      "min-w-[185px] rounded-xl border-2 px-3 py-2.5 shadow-lg select-none",
      "border-blue-500/60 bg-blue-950/50",
      selected && "ring-2 ring-white/25",
    )}>
      <Handle type="target" position={Position.Left} id="input"
        style={{ background: "#3b82f6", border: "2px solid #1d4ed8", width: 10, height: 10 }} />
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-[0.55rem] font-bold uppercase tracking-widest text-blue-400">{t("groupCondition")}</span>
      </div>
      <p className="text-sm font-medium text-white leading-tight">{data.label}</p>
      {summary && <p className="text-xs text-blue-300/60 mt-0.5">{summary}</p>}
      <div className="relative mt-2 h-8">
        <Handle type="source" position={Position.Right} id="true"
          style={{ top: "25%", background: "#22c55e", border: "2px solid #16a34a", width: 10, height: 10 }} />
        <span className="absolute right-[-22px] top-[0px] text-[9px] text-green-400 font-semibold leading-none">{t("conditionYes")}</span>
        <Handle type="source" position={Position.Right} id="false"
          style={{ top: "75%", background: "#ef4444", border: "2px solid #b91c1c", width: 10, height: 10 }} />
        <span className="absolute right-[-24px] bottom-[0px] text-[9px] text-red-400 font-semibold leading-none">{t("conditionNo")}</span>
      </div>
    </div>
  )
}

export function ActionNodeComp({ data, selected }: NodeProps) {
  const { t } = useTranslation("butler")
  const summary = paramSummary(data.subtype, data.params, t)
  return (
    <div className={cn(
      "min-w-[185px] rounded-xl border-2 px-3 py-2.5 shadow-lg select-none",
      "border-orange-500/60 bg-orange-950/50",
      selected && "ring-2 ring-white/25",
    )}>
      <Handle type="target" position={Position.Left} id="input"
        style={{ background: "#f97316", border: "2px solid #c2410c", width: 10, height: 10 }} />
      <div className="flex items-center gap-1.5 mb-1">
        <Zap className="h-3 w-3 text-orange-400" />
        <span className="text-[0.55rem] font-bold uppercase tracking-widest text-orange-400">{t("groupAction")}</span>
      </div>
      <p className="text-sm font-medium text-white leading-tight">{data.label}</p>
      {summary && <p className="text-xs text-orange-300/60 mt-0.5">{summary}</p>}
      <Handle type="source" position={Position.Right} id="output"
        style={{ background: "#f97316", border: "2px solid #c2410c", width: 10, height: 10 }} />
    </div>
  )
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const NODE_TYPES: NodeTypes = {
  triggerNode:   TriggerNodeComp as any,
  conditionNode: ConditionNodeComp as any,
  actionNode:    ActionNodeComp as any,
}
