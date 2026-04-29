import { useEffect, useRef, useState } from "react"
import { CheckCircle, Loader2, Mic, X, XCircle } from "lucide-react"
import { systemApi } from "./api"

export type VoiceInstallState = "confirm" | "starting" | "running" | "done" | "failed"

interface Props {
  state: VoiceInstallState
  errorMessage?: string | null
  onConfirm: () => void
  onClose: () => void
}

export function VoiceInstallModal({ state, errorMessage, onConfirm, onClose }: Props) {
  const [logLines, setLogLines] = useState<string[]>([])
  const logRef = useRef<HTMLPreElement>(null)
  const isPolling = state === "starting" || state === "running"

  useEffect(() => {
    if (!isPolling && state !== "done" && state !== "failed") return
    let alive = true
    async function fetchLog() {
      try {
        const r = await systemApi.voiceLog(300)
        if (!alive) return
        if (r.exists) setLogLines(r.lines)
      } catch { /* leise */ }
    }
    fetchLog()
    const interval = isPolling ? setInterval(fetchLog, 1500) : null
    return () => { alive = false; if (interval) clearInterval(interval) }
  }, [state, isPolling])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logLines])

  const dismissable = state === "confirm" || state === "done" || state === "failed"

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={() => dismissable && onClose()}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl mx-4 rounded-2xl border border-white/[8%] bg-zinc-900 shadow-2xl shadow-black/40 flex flex-col max-h-[85vh]"
      >
        <div className="flex items-center justify-between p-5 border-b border-white/[6%]">
          <div className="flex items-center gap-2">
            <Mic size={16} className="text-violet-400" />
            <h2 className="text-lg font-bold text-white">Voice Interface installieren</h2>
          </div>
          {dismissable && (
            <button onClick={onClose} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
              <X size={16} />
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {state === "confirm" && (
            <>
              <p className="text-sm text-zinc-200">
                Wyoming STT (faster-whisper) + TTS (Piper) via Docker installieren?
              </p>
              <ul className="text-xs text-zinc-400 space-y-1 list-disc list-inside">
                <li>Docker wird installiert falls nicht vorhanden</li>
                <li>Container-Images werden heruntergeladen (~1–2 GB)</li>
                <li>STT läuft auf Port 10300, TTS auf Port 10200</li>
                <li>Container starten automatisch bei jedem System-Neustart</li>
              </ul>
            </>
          )}

          {(state === "starting" || state === "running") && (
            <div className="flex items-center gap-2 text-sm text-amber-300">
              <Loader2 size={14} className="animate-spin" />
              <span>
                {state === "starting"
                  ? "Installation wird gestartet…"
                  : "Installation läuft — Docker-Images werden heruntergeladen…"}
              </span>
            </div>
          )}

          {state === "done" && (
            <div className="flex items-center gap-2 text-sm text-emerald-300">
              <CheckCircle size={14} />
              <span>Voice Interface erfolgreich installiert — STT Port 10300 · TTS Port 10200</span>
            </div>
          )}

          {state === "failed" && (
            <div className="flex items-center gap-2 text-sm text-rose-300">
              <XCircle size={14} />
              <span>Installation fehlgeschlagen: {errorMessage ?? "Unbekannter Fehler"}</span>
            </div>
          )}

          {state !== "confirm" && (
            <div className="space-y-1.5">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Installations-Log</p>
              <pre
                ref={logRef}
                className="rounded-lg border border-white/[6%] bg-zinc-950 p-3 text-[11px] font-mono leading-relaxed text-zinc-300 overflow-x-auto whitespace-pre-wrap min-h-[240px] max-h-[400px]"
              >
                {logLines.length > 0
                  ? logLines.join("")
                  : <span className="text-zinc-600">Warte auf Log-Ausgabe…</span>}
              </pre>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 p-5 border-t border-white/[6%]">
          {state === "confirm" && (
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
              >
                Abbrechen
              </button>
              <button
                onClick={onConfirm}
                className="px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium shadow-md shadow-violet-900/20"
              >
                Installieren
              </button>
            </>
          )}
          {(state === "done" || state === "failed") && (
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium shadow-md shadow-violet-900/20"
            >
              Schließen
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
