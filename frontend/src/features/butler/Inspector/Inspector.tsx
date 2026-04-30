import { Trash2 } from "lucide-react"
import { useFlowStore } from "../useFlowStore"
import { findSpec } from "../useRegistry"
import type { RegistryMeta } from "../types"
import { Field } from "./Field"

interface Props {
  registry: RegistryMeta
}

export function Inspector({ registry }: Props) {
  const flow = useFlowStore((s) => s.flow)
  const selectedId = useFlowStore((s) => s.selectedNodeId)
  const patchParams = useFlowStore((s) => s.patchParams)
  const patchNode = useFlowStore((s) => s.patchNode)
  const removeNode = useFlowStore((s) => s.removeNode)

  if (!flow || !selectedId) {
    return (
      <div className="h-full flex items-center justify-center text-xs text-zinc-500 px-6 text-center">
        Wähle einen Node aus oder ziehe einen aus der Palette.
      </div>
    )
  }

  const node = flow.nodes.find((n) => n.id === selectedId)
  if (!node) return null

  const spec = findSpec(registry, node.type, node.subtype)

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-3 border-b border-white/[8%] flex-shrink-0">
        <p className="text-[10px] uppercase tracking-wider text-zinc-500">{node.type}</p>
        <p className="text-sm font-semibold text-zinc-100 mt-0.5">
          {spec?.label || node.subtype}
        </p>
        {spec?.description && (
          <p className="text-[11px] text-zinc-500 mt-1 leading-relaxed">{spec.description}</p>
        )}
      </div>

      <div className="flex-1 min-h-0 overflow-auto px-4 py-3 space-y-3">
        <div className="space-y-1">
          <label className="text-[11px] text-zinc-400">Label (optional)</label>
          <input type="text" value={node.label ?? ""}
            placeholder={spec?.label || node.subtype}
            onChange={(e) => patchNode(node.id, { label: e.target.value || null })}
            className="w-full px-2 py-1 text-xs bg-white/[3%] border border-white/[8%] rounded-md placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50" />
        </div>

        {!spec && (
          <div className="text-[11px] text-rose-300 bg-rose-500/10 border border-rose-500/20 rounded-md px-2 py-1">
            Unbekannter Subtype „{node.subtype}" — kein Param-Schema verfügbar.
          </div>
        )}

        {spec?.params.map((p) => (
          <Field key={p.key} schema={p}
            value={node.params[p.key]}
            onChange={(v) => patchParams(node.id, { [p.key]: v })} />
        ))}
      </div>

      <div className="px-4 py-3 border-t border-white/[8%] flex-shrink-0">
        <button onClick={() => removeNode(node.id)}
          className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs text-rose-300 hover:bg-rose-500/10">
          <Trash2 size={11} /> Knoten löschen
        </button>
      </div>
    </div>
  )
}
