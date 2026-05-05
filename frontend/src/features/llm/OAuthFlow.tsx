import { useState } from "react"
import { ExternalLink, Loader2 } from "lucide-react"
import { llmApi } from "./api"

export function OAuthFlow({
  providerId,
  onConnected,
  onCancel,
}: {
  providerId: string
  onConnected: () => void
  onCancel?: () => void
}) {
  const [step, setStep] = useState<1 | 2>(1)
  const [authUrl, setAuthUrl] = useState("")
  const [code, setCode] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function startFlow() {
    setBusy(true); setError(null)
    try {
      const r = await llmApi.oauthStart(providerId)
      setAuthUrl(r.authorize_url)
      window.open(r.authorize_url, "_blank", "noopener,noreferrer")
      setStep(2)
    } catch (e) {
      setError(e instanceof Error ? e.message : "OAuth-Start fehlgeschlagen")
    } finally { setBusy(false) }
  }

  async function exchange() {
    if (!code.trim()) return
    setBusy(true); setError(null)
    try {
      await llmApi.oauthExchange(providerId, code.trim())
      onConnected()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Token-Tausch fehlgeschlagen")
    } finally { setBusy(false) }
  }

  return (
    <div className="space-y-3 p-3 rounded-lg bg-violet-500/[6%] border border-violet-500/30">
      <p className="text-xs font-semibold uppercase tracking-widest text-violet-300">
        OAuth-Login — Schritt {step} von 2
      </p>

      {step === 1 && (
        <div className="space-y-2">
          <p className="text-xs text-zinc-400">
            Login bei OpenAI/ChatGPT. Du wirst danach auf <code className="text-zinc-300">localhost:1455</code> umgeleitet —
            das wird im Browser eine "Diese Seite kann nicht erreicht werden"-Fehlermeldung zeigen.
            <strong className="text-zinc-200"> Das ist normal.</strong> Du kopierst die ganze URL aus
            dem Browser-Adressfeld in Schritt 2.
          </p>
          <div className="flex gap-2">
            <button onClick={startFlow} disabled={busy}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium disabled:opacity-40">
              {busy ? <Loader2 size={13} className="animate-spin" /> : <ExternalLink size={13} />}
              Login öffnen
            </button>
            {onCancel && (
              <button onClick={onCancel}
                className="px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
                Abbrechen
              </button>
            )}
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-2">
          <p className="text-xs text-zinc-400">
            Kopier die ganze URL aus dem Browser-Adressfeld
            (<code className="text-zinc-300">http://localhost:1455/auth/callback?code=...&state=...</code>)
            und füge sie hier ein:
          </p>
          {authUrl && (
            <a href={authUrl} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[11px] text-violet-300 hover:text-violet-200 underline">
              <ExternalLink size={11} /> Login-Seite erneut öffnen
            </a>
          )}
          <textarea value={code} onChange={(e) => setCode(e.target.value)}
            rows={3} placeholder="http://localhost:1455/auth/callback?code=...&state=..."
            className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-zinc-200 text-xs font-mono placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50 resize-none" />
          {error && <p className="text-xs text-rose-400">{error}</p>}
          <div className="flex gap-2">
            <button onClick={exchange} disabled={busy || !code.trim()}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium disabled:opacity-40">
              {busy && <Loader2 size={13} className="animate-spin" />}
              Verbinden
            </button>
            <button onClick={() => setStep(1)} disabled={busy}
              className="px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
              Zurück
            </button>
            {onCancel && (
              <button onClick={onCancel} disabled={busy}
                className="px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
                Abbrechen
              </button>
            )}
          </div>
        </div>
      )}
      {error && step === 1 && <p className="text-xs text-rose-400">{error}</p>}
    </div>
  )
}
