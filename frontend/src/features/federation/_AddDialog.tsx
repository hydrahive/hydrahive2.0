import { useState } from "react"
import { federationApi } from "./api"

interface Props {
  onClose: () => void
  onCreated: () => void
}

export function AddWorkstationDialog({ onClose, onCreated }: Props) {
  const [name, setName] = useState("")
  const [url, setUrl] = useState("")
  const [token, setToken] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim() || !url.trim()) return
    setSaving(true); setError(null)
    try {
      await federationApi.create(name.trim(), url.trim(), token.trim())
      onCreated()
    } catch (err: any) {
      setError(err?.message ?? "Fehler beim Speichern")
    } finally {
      setSaving(false)
    }
  }

  const input = "w-full bg-zinc-800/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-zinc-900 border border-white/10 rounded-2xl w-full max-w-md shadow-2xl">
        <div className="px-5 py-4 border-b border-white/8">
          <h2 className="text-sm font-semibold text-zinc-100">Workstation hinzufügen</h2>
          <p className="text-xs text-zinc-500 mt-0.5">A2A-kompatible Workstation registrieren</p>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-3">
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">Name</label>
            <input
              className={input}
              placeholder="projektx-till"
              value={name}
              onChange={e => setName(e.target.value)}
              required
            />
            <p className="text-[10px] text-zinc-600 mt-1">
              Wird als @-Adresse genutzt: <code className="text-violet-400">geralt@{name || "name"}</code>
            </p>
          </div>
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">URL</label>
            <input
              className={input}
              placeholder="http://192.168.3.25:8080"
              value={url}
              onChange={e => setUrl(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">Remote-Token (PROJEKTX_REMOTE_TOKEN)</label>
            <input
              className={input}
              type="password"
              placeholder="optional — für /remote/* Zugriff"
              value={token}
              onChange={e => setToken(e.target.value)}
            />
          </div>
          {error && <p className="text-xs text-rose-400">{error}</p>}
          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              disabled={saving || !name.trim() || !url.trim()}
              className="flex-1 py-2 rounded-lg text-sm font-medium bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white transition-colors"
            >
              {saving ? "Speichern…" : "Hinzufügen"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5 transition-colors"
            >
              Abbrechen
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
