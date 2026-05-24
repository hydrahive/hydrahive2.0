import { useState } from "react"
import { Download, X } from "lucide-react"
import { clientsApi } from "./api"
import type { ClientConfig } from "./types"

interface Props {
  onClose: () => void
  onCreated: () => void
}

function downloadConfig(config: ClientConfig) {
  const slug = config.name.replace(/\s+/g, "_").toLowerCase()
  const blob = new Blob([JSON.stringify(config, null, 2)], { type: "application/json" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `hh2-client-${slug}.json`
  a.click()
  URL.revokeObjectURL(url)
}

export function NewClientDialog({ onClose, onCreated }: Props) {
  const [name, setName] = useState("")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ keyId: string; config: ClientConfig } | null>(null)
  const [error, setError] = useState("")

  async function handleCreate() {
    if (!name.trim()) return
    setLoading(true)
    setError("")
    try {
      const data = await clientsApi.create(name.trim())
      setResult({ keyId: data.key_id, config: data.config })
      onCreated()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Fehler beim Erstellen")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-lg rounded-2xl border border-white/[8%] bg-zinc-900 p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-zinc-100">Neuen Client anbinden</h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 transition-colors">
            <X size={16} />
          </button>
        </div>

        {!result ? (
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-zinc-400 mb-1.5">Client-Name</label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleCreate()}
                placeholder="z.B. ProjektX Phone, ProjektX Laptop"
                className="w-full rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20"
                autoFocus
              />
            </div>
            {error && <p className="text-xs text-red-400">{error}</p>}
            <p className="text-xs text-zinc-500">
              Jeder Client erhält einen eigenen API-Key.
              Der Key wird nur einmalig angezeigt — nach dem Download nicht wiederherstellbar.
            </p>
            <div className="flex justify-end gap-2 pt-1">
              <button
                onClick={onClose}
                className="px-3 py-1.5 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
              >
                Abbrechen
              </button>
              <button
                onClick={handleCreate}
                disabled={loading || !name.trim()}
                className="px-4 py-1.5 rounded-lg text-sm bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors"
              >
                {loading ? "Erstelle…" : "Config generieren"}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 text-xs text-emerald-300">
              Config für <strong>{result.config.name}</strong> wurde generiert.
              Lade die Datei jetzt herunter — der API-Key kann danach nicht mehr abgerufen werden.
            </div>

            <div className="rounded-lg border border-white/[6%] bg-zinc-800/60 p-3 space-y-1.5 text-xs font-mono">
              {result.config.hh2.api_url && (
                <div><span className="text-zinc-500">URL: </span><span className="text-zinc-300">{result.config.hh2.api_url}</span></div>
              )}
              {result.config.tailscale?.dns_name && (
                <div><span className="text-zinc-500">Tailscale: </span><span className="text-zinc-300">{result.config.tailscale.dns_name}</span></div>
              )}
              {result.config.tailscale?.authkey ? (
                <div><span className="text-zinc-500">Authkey: </span><span className="text-emerald-400">✓ generiert</span></div>
              ) : (
                <div><span className="text-zinc-500">Authkey: </span><span className="text-zinc-500">— (Tailscale Admin nicht konfiguriert)</span></div>
              )}
              {result.config.agentlink ? (
                <div><span className="text-zinc-500">AgentLink: </span><span className="text-zinc-300">{result.config.agentlink.url}</span></div>
              ) : (
                <div><span className="text-zinc-500">AgentLink: </span><span className="text-zinc-500">— nicht konfiguriert</span></div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-1">
              <button
                onClick={onClose}
                className="px-3 py-1.5 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
              >
                Schließen
              </button>
              <button
                onClick={() => downloadConfig(result.config)}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-sm bg-violet-600 hover:bg-violet-500 text-white transition-colors"
              >
                <Download size={13} />
                Config herunterladen
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
