import { useState } from "react"
import { KeyRound, Save } from "lucide-react"
import { streamingApi } from "./api"
import type { StreamingCredentials } from "./types"

interface Props {
  creds: StreamingCredentials | null
  onSaved: () => void
}

const input = "w-full bg-zinc-800/60 border border-white/10 rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50"

export function CredentialsForm({ creds, onSaved }: Props) {
  const [open, setOpen] = useState(!creds)
  const [username, setUsername] = useState(creds?.username ?? "")
  const [password, setPassword] = useState("")
  const [plexPath, setPlexPath] = useState(creds?.plex_path ?? "/media/plex")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!username.trim()) return
    if (!password.trim() && !creds?.has_password) return
    setSaving(true); setError(null)
    try {
      await streamingApi.saveCredentials(username.trim(), password, plexPath.trim())
      onSaved()
      setOpen(false)
    } catch (err: any) {
      setError(err?.message ?? "Fehler beim Speichern")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-xl border border-white/10 bg-zinc-900/60 overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-2 px-4 py-3 text-sm text-zinc-300 hover:text-zinc-100 transition-colors"
      >
        <KeyRound size={14} className="text-violet-400" />
        <span className="font-medium">Ghostflix-Login</span>
        {creds && !open && (
          <span className="ml-auto text-xs text-zinc-500">{creds.username}</span>
        )}
      </button>

      {open && (
        <form onSubmit={handleSave} className="border-t border-white/5 px-4 pb-4 pt-3 space-y-3">
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">E-Mail / Benutzername</label>
            <input className={input} value={username} onChange={e => setUsername(e.target.value)}
              placeholder="bibs@beispiel.de" required />
          </div>
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">Passwort</label>
            <input className={input} type="password" value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder={creds?.has_password ? "••••••• (leer = unverändert)" : "Ghostflix-Passwort"}
              required={!creds?.has_password} />
          </div>
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">Plex-Ausgabepfad</label>
            <input className={input} value={plexPath} onChange={e => setPlexPath(e.target.value)}
              placeholder="/media/plex" required />
            <p className="text-[10px] text-zinc-600 mt-1">
              Serien landen in: <code className="text-violet-400">{plexPath}/Serientitel/Staffel 1/</code>
            </p>
          </div>
          {error && <p className="text-xs text-rose-400">{error}</p>}
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white transition-colors"
          >
            <Save size={12} />
            {saving ? "Speichern…" : "Speichern"}
          </button>
        </form>
      )}
    </div>
  )
}
