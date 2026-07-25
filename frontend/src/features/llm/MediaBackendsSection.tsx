import { useEffect, useState } from "react"
import { Loader2, Plus, Trash2, Zap, Check, X } from "lucide-react"
import { mediaBackendsApi, type MediaBackend, type MediaWorkflow } from "./api"

/**
 * GUI zur Verwaltung lokaler Media-Backends (ComfyUI / Switch-Wrapper).
 * Spec: docs/specs/local-video-backends.md (E3). Alles ohne JSON-Handarbeit:
 * ComfyUI-Workflows werden per Paste geparst und die Platzhalter vorgeschlagen.
 */
export function MediaBackendsSection() {
  const [backends, setBackends] = useState<MediaBackend[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    mediaBackendsApi.list()
      .then((r) => setBackends(r.media_backends))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function persist(next: MediaBackend[]) {
    setSaving(true)
    try {
      await mediaBackendsApi.save(next)
      setBackends(next)
    } finally { setSaving(false) }
  }

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-zinc-200">Lokale Media-Backends</h3>
        {saving && <span className="text-xs text-zinc-500">speichert…</span>}
      </div>
      <p className="text-xs text-zinc-500">
        ComfyUI (Node-Graph) oder Switch-Wrapper (sd-server). Modelle/Workflows erscheinen
        im Video-/Bild-Dialog neben den OpenRouter-Modellen.
      </p>

      {loading ? (
        <p className="text-xs text-zinc-500">Lade…</p>
      ) : (
        <div className="space-y-2">
          {backends.map((b, i) => (
            <BackendCard key={b.id} backend={b}
              onChange={(nb) => { const c = [...backends]; c[i] = nb; void persist(c) }}
              onDelete={() => void persist(backends.filter((_, j) => j !== i))} />
          ))}
          {backends.length === 0 && (
            <p className="text-xs text-zinc-600">Noch kein lokales Backend konfiguriert.</p>
          )}
        </div>
      )}

      {showAdd ? (
        <AddBackendForm
          onAdd={(nb) => { void persist([...backends, nb]); setShowAdd(false) }}
          onCancel={() => setShowAdd(false)} />
      ) : (
        <button onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-sm">
          <Plus size={14} /> Backend hinzufügen
        </button>
      )}
    </section>
  )
}

function TestButton({ type, apiBase }: { type: string; apiBase: string }) {
  const [state, setState] = useState<null | "ok" | "fail" | "busy">(null)
  const [detail, setDetail] = useState("")
  async function run() {
    setState("busy"); setDetail("")
    try {
      const r = await mediaBackendsApi.test(type, apiBase)
      if (r.ok) {
        setState("ok")
        setDetail(r.mode ? `Modus: ${r.mode}` : r.node_count != null ? `${r.node_count} Nodes` : "erreichbar")
      } else { setState("fail"); setDetail(r.error || `HTTP-Fehler`) }
    } catch { setState("fail"); setDetail("nicht erreichbar") }
  }
  return (
    <button onClick={run} disabled={!apiBase}
      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-200 disabled:opacity-40">
      {state === "busy" ? <Loader2 size={12} className="animate-spin" />
        : state === "ok" ? <Check size={12} className="text-emerald-400" />
        : state === "fail" ? <X size={12} className="text-rose-400" />
        : <Zap size={12} />}
      Verbindung testen{detail && <span className="text-zinc-500">· {detail}</span>}
    </button>
  )
}

function BackendCard({ backend, onChange, onDelete }: {
  backend: MediaBackend
  onChange: (b: MediaBackend) => void
  onDelete: () => void
}) {
  const [showWf, setShowWf] = useState(false)
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm text-zinc-100 font-medium">{backend.name}</div>
          <div className="text-xs text-zinc-500 font-mono">{backend.type} · {backend.api_base}</div>
        </div>
        <button onClick={onDelete} className="p-1.5 rounded text-zinc-500 hover:text-rose-400 hover:bg-white/5">
          <Trash2 size={14} />
        </button>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <TestButton type={backend.type} apiBase={backend.api_base} />
        {backend.type === "comfyui" && (
          <button onClick={() => setShowWf(!showWf)}
            className="px-2.5 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-200">
            Workflows ({backend.workflows?.length ?? 0})
          </button>
        )}
      </div>
      {showWf && backend.type === "comfyui" && (
        <WorkflowManager backend={backend} onChange={onChange} />
      )}
    </div>
  )
}

function AddBackendForm({ onAdd, onCancel }: {
  onAdd: (b: MediaBackend) => void; onCancel: () => void
}) {
  const [type, setType] = useState<"comfyui" | "switch-http">("comfyui")
  const [name, setName] = useState("")
  const [apiBase, setApiBase] = useState("")
  const valid = name.trim() && apiBase.trim()
  return (
    <div className="rounded-lg border border-zinc-700 bg-zinc-900 p-3 space-y-2">
      <div className="flex gap-2">
        <select value={type} onChange={(e) => setType(e.target.value as "comfyui" | "switch-http")}
          className="rounded-md bg-zinc-800 text-zinc-200 text-sm px-2 py-1.5 border border-zinc-700">
          <option value="comfyui">ComfyUI</option>
          <option value="switch-http">Switch-Wrapper (sd-server)</option>
        </select>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name (z.B. Muskeln1)"
          className="flex-1 rounded-md bg-zinc-800 text-zinc-200 text-sm px-2 py-1.5 border border-zinc-700" />
      </div>
      <input value={apiBase} onChange={(e) => setApiBase(e.target.value)}
        placeholder={type === "comfyui" ? "http://muskeln1:8189" : "http://muskeln2:9700"}
        className="w-full rounded-md bg-zinc-800 text-zinc-200 text-sm px-2 py-1.5 border border-zinc-700 font-mono" />
      <div className="flex gap-2">
        <button disabled={!valid}
          onClick={() => onAdd({ id: name.trim().toLowerCase().replace(/\s+/g, "-"),
            type, name: name.trim(), api_base: apiBase.trim(), workflows: [] })}
          className="px-3 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-sm disabled:opacity-40">
          Hinzufügen
        </button>
        <button onClick={onCancel} className="px-3 py-1.5 rounded-md bg-zinc-800 text-zinc-300 text-sm">Abbrechen</button>
      </div>
    </div>
  )
}

const PARAM_KEYS = ["prompt", "seed", "width", "height", "frames", "image_url"] as const

function WorkflowManager({ backend, onChange }: {
  backend: MediaBackend; onChange: (b: MediaBackend) => void
}) {
  const [adding, setAdding] = useState(false)
  const wfs = backend.workflows ?? []
  return (
    <div className="mt-2 space-y-2 border-t border-zinc-800 pt-2">
      {wfs.map((w, i) => (
        <div key={w.id} className="flex items-center justify-between text-xs">
          <span className="text-zinc-300">{w.label} <span className="text-zinc-600">({w.category})</span></span>
          <button onClick={() => onChange({ ...backend, workflows: wfs.filter((_, j) => j !== i) })}
            className="p-1 rounded text-zinc-500 hover:text-rose-400"><Trash2 size={12} /></button>
        </div>
      ))}
      {adding ? (
        <WorkflowForm
          onAdd={(w) => { onChange({ ...backend, workflows: [...wfs, w] }); setAdding(false) }}
          onCancel={() => setAdding(false)} />
      ) : (
        <button onClick={() => setAdding(true)}
          className="flex items-center gap-1.5 px-2 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-200">
          <Plus size={12} /> Workflow hinzufügen
        </button>
      )}
    </div>
  )
}

function WorkflowForm({ onAdd, onCancel }: {
  onAdd: (w: MediaWorkflow) => void; onCancel: () => void
}) {
  const [label, setLabel] = useState("")
  const [category, setCategory] = useState<"video" | "image">("video")
  const [json, setJson] = useState("")
  const [nodes, setNodes] = useState<{ id: string; class_type: string; inputs: string[] }[]>([])
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [graph, setGraph] = useState<Record<string, unknown> | null>(null)
  const [err, setErr] = useState("")

  async function parse() {
    setErr("")
    let g: Record<string, unknown>
    try { g = JSON.parse(json) } catch { setErr("Kein gültiges JSON"); return }
    try {
      const r = await mediaBackendsApi.parseWorkflow(g)
      setNodes(r.nodes); setMapping(r.suggestions); setGraph(g)
    } catch { setErr("Workflow konnte nicht geparst werden (API-Format nötig)") }
  }

  const addrOptions = nodes.flatMap((n) => n.inputs.map((f) => `${n.id}.inputs.${f}`))

  return (
    <div className="rounded-md border border-zinc-700 bg-zinc-950/60 p-2 space-y-2">
      <div className="flex gap-2">
        <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Label (z.B. LTX Text→Video)"
          className="flex-1 rounded bg-zinc-800 text-zinc-200 text-xs px-2 py-1 border border-zinc-700" />
        <select value={category} onChange={(e) => setCategory(e.target.value as "video" | "image")}
          className="rounded bg-zinc-800 text-zinc-200 text-xs px-2 py-1 border border-zinc-700">
          <option value="video">Video</option>
          <option value="image">Bild</option>
        </select>
      </div>
      <textarea value={json} onChange={(e) => setJson(e.target.value)}
        placeholder='ComfyUI-Workflow im API-Format einfügen (ComfyUI → "Save (API Format)")'
        className="w-full h-24 rounded bg-zinc-800 text-zinc-300 text-xs px-2 py-1 border border-zinc-700 font-mono" />
      {err && <p className="text-xs text-rose-400">{err}</p>}
      {!graph ? (
        <button onClick={parse} disabled={!json.trim()}
          className="px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs disabled:opacity-40">
          Workflow analysieren
        </button>
      ) : (
        <div className="space-y-1.5">
          <p className="text-xs text-zinc-500">Platzhalter zuordnen (Vorschläge vorbelegt):</p>
          {PARAM_KEYS.map((key) => (
            <div key={key} className="flex items-center gap-2">
              <span className="text-xs text-zinc-400 w-16">{key}</span>
              <select value={mapping[key] ?? ""} onChange={(e) => setMapping({ ...mapping, [key]: e.target.value })}
                className="flex-1 rounded bg-zinc-800 text-zinc-300 text-xs px-2 py-1 border border-zinc-700">
                <option value="">— nicht gesetzt —</option>
                {addrOptions.map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>
          ))}
          <div className="flex gap-2 pt-1">
            <button disabled={!label.trim()}
              onClick={() => onAdd({
                id: label.trim().toLowerCase().replace(/\s+/g, "-"),
                label: label.trim(), category, graph: graph!,
                placeholders: Object.fromEntries(Object.entries(mapping).filter(([, v]) => v)),
              })}
              className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs disabled:opacity-40">
              Workflow speichern
            </button>
            <button onClick={onCancel} className="px-2.5 py-1 rounded bg-zinc-800 text-zinc-300 text-xs">Abbrechen</button>
          </div>
        </div>
      )}
      {!graph && (
        <button onClick={onCancel} className="text-xs text-zinc-500 hover:text-zinc-300">Abbrechen</button>
      )}
    </div>
  )
}
