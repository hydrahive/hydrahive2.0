import { useState } from "react"
import { ExternalLink, Check, AlertTriangle } from "lucide-react"
import { oauthApi } from "./api"

interface Props {
  onConnected: (expiresAt: number) => void
  onCancel: () => void
}

/** OAuth-Login für Anthropic via Claude.ai.
 *
 * Schritt 1: Backend erzeugt Authorize-URL + state. User öffnet URL.
 * Schritt 2: claude.ai redirected zu http://localhost:53692/callback?code=...
 *            Browser zeigt "Connection refused" — User kopiert die URL oder
 *            den Code-Parameter und paste hier rein.
 * Schritt 3: Backend tauscht Code → Token, schreibt in llm.json.
 */
export function AnthropicOAuthLogin({ onConnected, onCancel }: Props) {
  const [stage, setStage] = useState<"start" | "wait" | "exchanging" | "error">("start")
  const [authorizeUrl, setAuthorizeUrl] = useState("")
  const [state, setState] = useState("")
  const [codeOrUrl, setCodeOrUrl] = useState("")
  const [error, setError] = useState("")

  async function start() {
    try {
      const res = await oauthApi.startAnthropic()
      setAuthorizeUrl(res.authorize_url)
      setState(res.state)
      setStage("wait")
      window.open(res.authorize_url, "_blank", "noopener,noreferrer")
    } catch (e) {
      setError(String(e))
      setStage("error")
    }
  }

  async function exchange() {
    setStage("exchanging")
    setError("")
    try {
      const res = await oauthApi.exchangeAnthropic(codeOrUrl, state)
      onConnected(res.expires_at)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg)
      setStage("wait")
    }
  }

  return (
    <div className="p-4 rounded-xl border border-violet-500/30 bg-violet-500/[5%] space-y-3">
      <p className="text-sm font-medium text-violet-200">Anthropic OAuth-Login (Claude Pro/Max)</p>

      {stage === "start" && (
        <>
          <p className="text-xs text-zinc-400">
            Du wirst zu claude.ai weitergeleitet. Nach dem Autorisieren versucht der Browser
            <code className="mx-1 px-1.5 py-0.5 rounded bg-white/[5%] text-zinc-300">localhost:53692/callback</code>
            zu öffnen — das schlägt fehl ("Connection refused"), aber die URL in der Adressleiste
            enthält den Code. Diese kopierst du hierher zurück.
          </p>
          <div className="flex gap-2">
            <button onClick={start}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white text-sm font-medium transition-all">
              <ExternalLink size={14} /> Mit Claude.ai verbinden
            </button>
            <button onClick={onCancel}
              className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
              Abbrechen
            </button>
          </div>
        </>
      )}

      {(stage === "wait" || stage === "exchanging") && (
        <>
          <p className="text-xs text-zinc-400">
            Wenn der claude.ai-Tab nicht geöffnet wurde:&nbsp;
            <a href={authorizeUrl} target="_blank" rel="noopener noreferrer"
              className="underline text-violet-300 hover:text-violet-200">manuell öffnen</a>
          </p>
          <div>
            <label className="block text-xs text-zinc-500 mb-1">
              Callback-URL oder Code (aus der Adressleiste nach dem Autorisieren)
            </label>
            <input type="text" value={codeOrUrl} onChange={(e) => setCodeOrUrl(e.target.value)}
              placeholder="http://localhost:53692/callback?code=...&state=..."
              disabled={stage === "exchanging"}
              className="w-full px-3 py-2 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-200 text-sm font-mono placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50 disabled:opacity-60" />
          </div>
          {error && (
            <div className="flex items-start gap-2 p-2 rounded-lg bg-rose-500/10 border border-rose-500/30">
              <AlertTriangle size={14} className="mt-0.5 text-rose-300 shrink-0" />
              <p className="text-xs text-rose-200">{error}</p>
            </div>
          )}
          <div className="flex gap-2">
            <button onClick={exchange} disabled={!codeOrUrl.trim() || stage === "exchanging"}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed transition-all">
              <Check size={14} /> {stage === "exchanging" ? "Verbinde..." : "Verbinden"}
            </button>
            <button onClick={onCancel} disabled={stage === "exchanging"}
              className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5 disabled:opacity-40">
              Abbrechen
            </button>
          </div>
        </>
      )}

      {stage === "error" && (
        <>
          <div className="flex items-start gap-2 p-2 rounded-lg bg-rose-500/10 border border-rose-500/30">
            <AlertTriangle size={14} className="mt-0.5 text-rose-300 shrink-0" />
            <p className="text-xs text-rose-200">{error || "Login konnte nicht gestartet werden"}</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setStage("start")}
              className="px-4 py-2 rounded-lg bg-white/[5%] hover:bg-white/[8%] text-sm text-zinc-300">
              Erneut versuchen
            </button>
            <button onClick={onCancel}
              className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
              Abbrechen
            </button>
          </div>
        </>
      )}
    </div>
  )
}
