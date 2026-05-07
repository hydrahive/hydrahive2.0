import { useEffect, useRef, useState } from "react"
import { X, Terminal } from "lucide-react"
import type { Extension, InstallParam } from "./types"
import { streamAction } from "./api"

interface Props {
  ext: Extension
  action: "install" | "uninstall"
  onClose: (refreshNeeded: boolean) => void
}

export function InstallModal({ ext, action, onClose }: Props) {
  const [params, setParams] = useState<Record<string, string>>({})
  const [phase, setPhase] = useState<"params" | "running" | "done">(
    action === "install" && ext.install_params.length > 0 ? "params" : "running"
  )
  const [lines, setLines] = useState<string[]>([])
  const [failed, setFailed] = useState(false)
  const logRef = useRef<HTMLDivElement>(null)
  const stopRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    if (phase !== "running") return
    stopRef.current = streamAction(
      ext.id, action, params,
      (line) => setLines((l) => [...l.slice(-500), line]),
      () => setPhase("done"),
      (msg) => { setLines((l) => [...l, `[FEHLER] ${msg}`]); setFailed(true); setPhase("done") },
    )
    return () => stopRef.current?.()
  }, [phase])

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight)
  }, [lines])

  const requiredMissing = ext.install_params
    .filter((p: InstallParam) => p.required && !params[p.key]?.trim())

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-zinc-900 border border-white/[8%] rounded-xl shadow-2xl flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-white/[6%]">
          <Terminal size={16} className="text-violet-400" />
          <span className="font-semibold text-zinc-100 text-sm">
            {action === "install" ? "Installieren" : "Deinstallieren"}: {ext.name}
          </span>
          <div className="flex-1" />
          {phase === "running" && (
            <span className="text-xs text-amber-400 animate-pulse">Läuft — bitte nicht schließen</span>
          )}
          {phase !== "running" && (
            <button onClick={() => onClose(phase === "done" && !failed)}
              className="p-1 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/[5%]">
              <X size={16} />
            </button>
          )}
        </div>

        {/* Params */}
        {phase === "params" && (
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {ext.install_params.map((p: InstallParam) => (
              <div key={p.key}>
                <label className="block text-xs font-medium text-zinc-300 mb-1">
                  {p.label}{p.required && <span className="text-rose-400 ml-1">*</span>}
                </label>
                {p.description && (
                  <p className="text-[11px] text-zinc-500 mb-1.5">{p.description}</p>
                )}
                <input
                  type={p.type === "password" ? "password" : "text"}
                  placeholder={p.placeholder}
                  value={params[p.key] ?? ""}
                  onChange={(e) => setParams((prev) => ({ ...prev, [p.key]: e.target.value }))}
                  className="w-full bg-zinc-800 border border-white/[8%] rounded-lg px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-violet-500/60"
                />
              </div>
            ))}
            <button
              disabled={requiredMissing.length > 0}
              onClick={() => setPhase("running")}
              className="w-full py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors">
              Installation starten
            </button>
          </div>
        )}

        {/* Log */}
        {(phase === "running" || phase === "done") && (
          <>
            <div ref={logRef}
              className="flex-1 overflow-y-auto p-4 font-mono text-xs leading-relaxed bg-zinc-950/50 min-h-[300px]">
              {lines.length === 0 && <span className="text-zinc-600">Warte auf Ausgabe…</span>}
              {lines.map((l, i) => (
                <div key={i} className={
                  l.startsWith("[OK]") ? "text-emerald-400" :
                  l.startsWith("[FEHLER]") || l.startsWith("[ERROR]") ? "text-rose-400" :
                  l.startsWith("[WARN]") ? "text-amber-400" :
                  "text-zinc-300"
                }>{l}</div>
              ))}
            </div>
            {phase === "done" && (
              <div className="px-5 py-4 border-t border-white/[6%] flex items-center justify-between">
                <span className={`text-sm font-medium ${failed ? "text-rose-400" : "text-emerald-400"}`}>
                  {failed ? "Fehlgeschlagen" : "Erfolgreich abgeschlossen"}
                </span>
                <button onClick={() => onClose(!failed)}
                  className="px-4 py-1.5 rounded-lg bg-zinc-700 hover:bg-zinc-600 text-zinc-100 text-sm transition-colors">
                  Schließen
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
