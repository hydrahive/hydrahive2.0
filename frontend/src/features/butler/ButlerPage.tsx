import { useCallback, useEffect, useState } from "react"
import { Plus, Save, Trash2, Play } from "lucide-react"
import type { Flow } from "./types"
import { butlerApi } from "./api"
import { useFlowStore } from "./useFlowStore"
import { useRegistry } from "./useRegistry"
import { Canvas } from "./Canvas/Canvas"
import { NodePalette } from "./Palette/NodePalette"
import { Inspector } from "./Inspector/Inspector"
import { DryRunModal } from "./DryRunModal"

function emptyFlow(id: string, name: string): Flow {
  return {
    flow_id: id, name, owner: "", enabled: false, scope: "user", scope_id: null,
    nodes: [], edges: [],
    created_at: null, modified_at: null, modified_by: null,
  }
}

export function ButlerPage() {
  const { registry, error: regError } = useRegistry()
  const flow = useFlowStore((s) => s.flow)
  const dirty = useFlowStore((s) => s.dirty)
  const setFlow = useFlowStore((s) => s.setFlow)
  const patchMeta = useFlowStore((s) => s.patchMeta)
  const markClean = useFlowStore((s) => s.markClean)

  const [flows, setFlows] = useState<Flow[]>([])
  const [error, setError] = useState<string | null>(null)
  const [showDryRun, setShowDryRun] = useState(false)

  const refresh = useCallback(async () => {
    try {
      setFlows(await butlerApi.list())
      setError(null)
    } catch (e) { setError(e instanceof Error ? e.message : String(e)) }
  }, [])

  useEffect(() => { void refresh() }, [refresh])

  async function newFlow() {
    const name = prompt("Name des Flows:")?.trim()
    if (!name) return
    const id = name.toLowerCase().replace(/[^a-z0-9_-]+/g, "_").slice(0, 60)
    setFlow(emptyFlow(id, name))
  }

  async function loadFlow(id: string) {
    if (dirty && !confirm("Änderungen verwerfen?")) return
    try {
      setFlow(await butlerApi.get(id))
    } catch (e) { setError(e instanceof Error ? e.message : String(e)) }
  }

  async function save() {
    if (!flow) return
    try {
      const input = {
        flow_id: flow.flow_id, name: flow.name, enabled: flow.enabled,
        nodes: flow.nodes, edges: flow.edges,
        scope: flow.scope, scope_id: flow.scope_id,
      }
      const exists = flows.some((f) => f.flow_id === flow.flow_id)
      const saved = exists
        ? await butlerApi.update(flow.flow_id, input)
        : await butlerApi.create(input)
      setFlow(saved); markClean(); void refresh()
    } catch (e) { setError(e instanceof Error ? e.message : String(e)) }
  }

  async function remove() {
    if (!flow || !confirm(`Flow "${flow.name}" löschen?`)) return
    try {
      await butlerApi.remove(flow.flow_id)
      setFlow(null); void refresh()
    } catch (e) { setError(e instanceof Error ? e.message : String(e)) }
  }

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 4rem)" }}>
      <div className="flex items-center gap-2 px-4 py-2 border-b border-white/[8%] flex-shrink-0">
        <h1 className="text-sm font-bold text-white">Butler</h1>
        <select value={flow?.flow_id || ""} onChange={(e) => e.target.value && loadFlow(e.target.value)}
          className="px-2 py-1 text-xs bg-white/[3%] border border-white/[8%] rounded-md focus:outline-none focus:border-violet-500/50">
          <option value="">— Flow wählen —</option>
          {flows.map((f) => <option key={f.flow_id} value={f.flow_id}>{f.name}</option>)}
        </select>
        <button onClick={newFlow}
          className="flex items-center gap-1 px-2 py-1 rounded-md text-xs bg-white/[5%] border border-white/[8%] text-zinc-300 hover:text-white">
          <Plus size={11} /> Neu
        </button>

        {flow && (
          <>
            <input value={flow.name} onChange={(e) => patchMeta({ name: e.target.value })}
              className="ml-2 px-2 py-1 text-xs bg-white/[3%] border border-white/[8%] rounded-md focus:outline-none focus:border-violet-500/50" />
            <label className="flex items-center gap-1 text-[11px] text-zinc-400">
              <input type="checkbox" checked={flow.enabled}
                onChange={(e) => patchMeta({ enabled: e.target.checked })}
                className="accent-emerald-500" />
              aktiv
            </label>
            <div className="flex-1" />
            <button onClick={() => setShowDryRun(true)}
              className="flex items-center gap-1 px-2 py-1 rounded-md text-xs bg-violet-500/15 border border-violet-500/30 text-violet-200 hover:bg-violet-500/25">
              <Play size={11} /> Dry-Run
            </button>
            <button onClick={save} disabled={!dirty}
              className="flex items-center gap-1 px-2 py-1 rounded-md text-xs bg-emerald-500/15 border border-emerald-500/30 text-emerald-200 hover:bg-emerald-500/25 disabled:opacity-30">
              <Save size={11} /> {dirty ? "Speichern*" : "Gespeichert"}
            </button>
            <button onClick={remove}
              className="p-1 rounded-md text-zinc-500 hover:text-rose-300">
              <Trash2 size={11} />
            </button>
          </>
        )}
      </div>

      {(error || regError) && (
        <div className="px-4 py-1.5 bg-rose-500/10 border-b border-rose-500/30 text-[11px] text-rose-200">
          {error || regError}
        </div>
      )}

      <div className="flex-1 min-h-0 grid grid-cols-[200px_1fr_280px]">
        <div className="border-r border-white/[8%] bg-zinc-950">
          {registry && <NodePalette registry={registry} />}
        </div>
        <div className="bg-zinc-950">
          <Canvas />
        </div>
        <div className="border-l border-white/[8%] bg-zinc-950">
          {registry && <Inspector registry={registry} />}
        </div>
      </div>

      {showDryRun && flow && <DryRunModal flow={flow} onClose={() => setShowDryRun(false)} />}
    </div>
  )
}
