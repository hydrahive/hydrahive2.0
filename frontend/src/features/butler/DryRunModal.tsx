import { useState } from "react"
import { Play, X } from "lucide-react"
import type { DryRunResult, Flow } from "./types"
import { butlerApi } from "./api"

interface Props {
  flow: Flow
  onClose: () => void
}

const SAMPLE_EVENTS: Record<string, string> = {
  "WhatsApp-Nachricht": JSON.stringify({
    event_type: "message", channel: "whatsapp",
    contact_id: "491234567890", contact_label: "Till", is_known: true,
    message_text: "Hallo, ich brauche Hilfe!",
  }, null, 2),
  "Webhook": JSON.stringify({
    event_type: "webhook", channel: "my-hook",
    payload: { foo: "bar" },
  }, null, 2),
  "Git-Push": JSON.stringify({
    event_type: "git",
    payload: { provider: "github", git_event: "push", repo: "hydrahive/hydrahive2.0",
               branch: "main", author: "till" },
  }, null, 2),
}

export function DryRunModal({ flow, onClose }: Props) {
  const [json, setJson] = useState<string>(SAMPLE_EVENTS["WhatsApp-Nachricht"])
  const [result, setResult] = useState<DryRunResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)

  async function run() {
    setRunning(true); setError(null); setResult(null)
    try {
      const event = JSON.parse(json)
      const r = await butlerApi.dryRun(flow.flow_id, event)
      setResult(r)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally { setRunning(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="w-full max-w-3xl rounded-xl border border-white/[10%] bg-zinc-950 shadow-2xl flex flex-col max-h-[80vh]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/[8%] flex-shrink-0">
          <p className="text-sm font-semibold text-zinc-200">Dry-Run — {flow.name}</p>
          <button onClick={onClose} className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-white/[5%]">
            <X size={16} />
          </button>
        </div>

        <div className="px-4 py-3 border-b border-white/[8%] flex-shrink-0 space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] text-zinc-400">Beispiele:</span>
            {Object.keys(SAMPLE_EVENTS).map((k) => (
              <button key={k} onClick={() => setJson(SAMPLE_EVENTS[k])}
                className="text-[10px] px-2 py-0.5 rounded bg-white/[5%] border border-white/[8%] text-zinc-400 hover:text-zinc-200">
                {k}
              </button>
            ))}
          </div>
          <textarea value={json} onChange={(e) => setJson(e.target.value)} rows={8}
            className="w-full px-2 py-1 text-xs font-mono bg-[#0b0b0f] border border-white/[8%] rounded-md focus:outline-none focus:border-violet-500/50" />
          <button onClick={run} disabled={running}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-violet-500/15 hover:bg-violet-500/25 border border-violet-500/30 text-violet-200 disabled:opacity-40">
            <Play size={12} /> Dry-Run starten
          </button>
          {error && <p className="text-[11px] text-rose-300">{error}</p>}
        </div>

        <div className="flex-1 min-h-0 overflow-auto px-4 py-3">
          {!result ? (
            <p className="text-xs text-zinc-500">Noch kein Lauf.</p>
          ) : !result.matched ? (
            <p className="text-xs text-zinc-400">Trigger matcht nicht — Flow wurde nicht ausgeführt.</p>
          ) : (
            <div className="space-y-1">
              <p className="text-[11px] text-zinc-500 mb-2">{result.trace.length} Knoten durchlaufen</p>
              {result.trace.map((t, i) => (
                <div key={i} className="text-[11px] font-mono flex items-baseline gap-2">
                  <span className="text-zinc-600 w-6">{i + 1}</span>
                  <span className="text-zinc-300 w-24 truncate">{t.subtype}</span>
                  <span className={
                    t.decision === "match" || t.decision === "true" || t.decision === "would_execute" ? "text-emerald-300" :
                    t.decision === "false" || t.decision === "no_match" ? "text-rose-300" :
                    t.decision === "error" ? "text-rose-400" : "text-zinc-500"
                  }>{t.decision}</span>
                  {t.detail && <span className="text-zinc-500 truncate">{t.detail}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
