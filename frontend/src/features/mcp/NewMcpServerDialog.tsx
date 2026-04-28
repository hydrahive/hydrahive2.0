import { useState } from "react"
import { X } from "lucide-react"
import { mcpApi } from "./api"

interface Props {
  onClose: () => void
  onCreated: (id: string) => void
}

type Transport = "stdio" | "http" | "sse"

export function NewMcpServerDialog({ onClose, onCreated }: Props) {
  const [id, setId] = useState("")
  const [name, setName] = useState("")
  const [transport, setTransport] = useState<Transport>("stdio")
  const [command, setCommand] = useState("")
  const [argsText, setArgsText] = useState("")
  const [envText, setEnvText] = useState("")
  const [url, setUrl] = useState("")
  const [description, setDescription] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setError(null)
    try {
      const env = Object.fromEntries(
        envText.split("\n").map((l) => l.trim()).filter(Boolean)
          .map((l) => l.split("=", 2)).filter((p) => p.length === 2)
      )
      const created = await mcpApi.create({
        id: id.trim(), name: name.trim(), transport, description, enabled: true,
        command: transport === "stdio" ? command : undefined,
        args: transport === "stdio" ? argsText.split(/\s+/).filter(Boolean) : undefined,
        env: transport === "stdio" ? env : undefined,
        url: transport !== "stdio" ? url : undefined,
      })
      onCreated(created.id)
    } catch (e) { setError(e instanceof Error ? e.message : "Fehler") }
    finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <form onSubmit={submit} onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg rounded-2xl border border-white/[8%] bg-zinc-900 p-6 shadow-2xl shadow-black/40 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">MCP-Server hinzufügen</h2>
          <button type="button" onClick={onClose} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
            <X size={16} />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-zinc-400">ID (a-z, 0-9, _ -)</label>
            <input value={id} onChange={(e) => setId(e.target.value)} required pattern="[a-zA-Z0-9_\-]+"
              placeholder="z.B. fs"
              className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm font-mono" />
          </div>
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-zinc-400">Anzeige-Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required
              placeholder="z.B. Filesystem"
              className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm" />
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-400">Transport</label>
          <select value={transport} onChange={(e) => setTransport(e.target.value as Transport)}
            className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm">
            <option value="stdio">stdio (lokaler Subprocess)</option>
            <option value="http">HTTP (streamable, modern)</option>
            <option value="sse">SSE (Server-Sent Events, legacy)</option>
          </select>
        </div>

        {transport === "stdio" && (
          <>
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-zinc-400">Command</label>
              <input value={command} onChange={(e) => setCommand(e.target.value)} required
                placeholder="z.B. npx"
                className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm font-mono" />
            </div>
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-zinc-400">Args (whitespace-getrennt)</label>
              <input value={argsText} onChange={(e) => setArgsText(e.target.value)}
                placeholder="z.B. -y @modelcontextprotocol/server-filesystem /tmp"
                className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm font-mono" />
            </div>
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-zinc-400">Env (KEY=VALUE pro Zeile)</label>
              <textarea value={envText} onChange={(e) => setEnvText(e.target.value)} rows={2}
                className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm font-mono" />
            </div>
          </>
        )}

        {(transport === "http" || transport === "sse") && (
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-zinc-400">URL</label>
            <input value={url} onChange={(e) => setUrl(e.target.value)} required
              className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm font-mono" />
          </div>
        )}

        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-400">Beschreibung</label>
          <input value={description} onChange={(e) => setDescription(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm" />
        </div>

        {error && (
          <p className="text-sm text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-3 py-2">{error}</p>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5">Abbrechen</button>
          <button type="submit" disabled={busy || !id.trim() || !name.trim()}
            className="px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-violet-900/20">
            Anlegen
          </button>
        </div>
      </form>
    </div>
  )
}
