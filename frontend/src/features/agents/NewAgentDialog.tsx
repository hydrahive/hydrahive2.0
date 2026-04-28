import { X } from "lucide-react"
import { useEffect, useState } from "react"
import { agentsApi } from "./api"
import type { AgentDefaults } from "./types"

interface Props {
  models: string[]
  defaultModel: string
  onClose: () => void
  onCreated: (id: string) => void
}

export function NewAgentDialog({ models, defaultModel, onClose, onCreated }: Props) {
  const [type, setType] = useState("specialist")
  const [name, setName] = useState("")
  const [model, setModel] = useState(defaultModel || models[0] || "")
  const [defaults, setDefaults] = useState<AgentDefaults | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => { agentsApi.getDefaults().then(setDefaults).catch(() => {}) }, [])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setError(null)
    try {
      const tools = defaults?.tools_per_type[type] ?? []
      const created = await agentsApi.create({
        type, name: name.trim(), llm_model: model, tools,
        description: "", temperature: 0.7, max_tokens: 4096,
        thinking_budget: 0, mcp_servers: [],
      })
      onCreated(created.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <form onSubmit={submit} onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-2xl border border-white/[8%] bg-zinc-900 p-6 shadow-2xl shadow-black/40 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">Neuen Agent anlegen</h2>
          <button type="button" onClick={onClose} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
            <X size={16} />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-zinc-400">Typ</label>
            <select value={type} onChange={(e) => setType(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm">
              <option value="master">Master</option>
              <option value="project">Projekt</option>
              <option value="specialist">Spezialist</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-zinc-400">Modell</label>
            <select value={model} onChange={(e) => setModel(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm">
              {models.length === 0 && <option value="">(kein Modell)</option>}
              {models.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-400">Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} required
            placeholder="z.B. Research-Bot"
            className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm placeholder:text-zinc-600" />
        </div>

        {defaults && (
          <p className="text-xs text-zinc-500">
            Default-Tools für <span className="font-mono text-zinc-400">{type}</span>: {(defaults.tools_per_type[type] ?? []).length}
          </p>
        )}

        {error && (
          <p className="text-sm text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-3 py-2">{error}</p>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
            Abbrechen
          </button>
          <button type="submit" disabled={busy || !name.trim() || !model}
            className="px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-violet-900/20">
            Anlegen
          </button>
        </div>
      </form>
    </div>
  )
}
