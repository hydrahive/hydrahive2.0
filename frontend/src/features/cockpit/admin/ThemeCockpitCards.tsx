import { useEffect, useRef, useState } from "react"
import { CheckCircle, Lock, Palette, RefreshCw, XCircle } from "lucide-react"
import type { AvailableTheme, InstalledTheme } from "@/features/themes/types"
import { installTheme, uninstallTheme, updateTheme } from "@/features/themes/api"

type Phase = "idle" | "running" | "done"
type Action = "update" | "uninstall"

/** Install-/Update-Log im Cockpit-Design (ohne box/zinc). */
function InstallLog({ lines, phase, failed }: { lines: string[]; phase: Phase; failed: boolean }) {
  const logRef = useRef<HTMLDivElement>(null)
  useEffect(() => { logRef.current?.scrollTo(0, logRef.current.scrollHeight) }, [lines])
  if (phase === "idle") return null
  return (
    <div ref={logRef} className="max-h-40 overflow-y-auto rounded-[4px] bg-[#0b111c] p-3 font-mono text-[11px] leading-relaxed">
      {lines.length === 0 && <span className="text-[#5b6675]">Warte …</span>}
      {lines.map((l, i) => (
        <div key={i} className={l.startsWith("[FEHLER]") || l.startsWith("[ERROR]") ? "text-rose-400" : "text-[#d7deea]"}>{l}</div>
      ))}
      {phase === "done" && (
        <div className={`mt-1 font-medium ${failed ? "text-rose-400" : "text-emerald-400"}`}>
          {failed ? "Fehlgeschlagen." : "Fertig — nach dem Neustart im Profil wählbar."}
        </div>
      )}
    </div>
  )
}

export function InstalledThemeCockpitCard({ th, onRefresh }: { th: InstalledTheme; onRefresh: () => void }) {
  const [phase, setPhase] = useState<Phase>("idle")
  const [action, setAction] = useState<Action>("update")
  const [lines, setLines] = useState<string[]>([])
  const [failed, setFailed] = useState(false)
  const stopRef = useRef<(() => void) | null>(null)

  function run(a: Action) {
    setAction(a); setPhase("running"); setLines([]); setFailed(false)
    const fn = a === "update" ? updateTheme : uninstallTheme
    stopRef.current = fn(th.id,
      (line) => setLines((l) => [...l.slice(-500), line]),
      () => { setPhase("done"); onRefresh() },
      (msg) => { setLines((l) => [...l, `[FEHLER] ${msg}`]); setFailed(true); setPhase("done") })
  }
  useEffect(() => () => stopRef.current?.(), [])

  return (
    <div className="flex flex-col gap-3 rounded-[6px] border border-[#2a364b] bg-[#111827] p-4">
      <div className="flex items-start gap-3">
        <div className="shrink-0 rounded-[4px] bg-emerald-500/10 p-2 text-emerald-400"><Palette size={18} /></div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-[#e8eef8]">{th.name ?? th.id}</span>
            {th.version && <span className="rounded-full border border-[#2a364b] bg-[#0d1420] px-1.5 py-0.5 text-[10px] text-[#8d9ab0]">v{th.version}</span>}
            {th.loaded ? (
              <span className="flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-400"><CheckCircle size={9} /> Installiert</span>
            ) : (
              <span className="flex items-center gap-1 rounded-full border border-rose-500/30 bg-rose-500/15 px-2 py-0.5 text-[10px] font-medium text-rose-400"><XCircle size={9} /> Fehler</span>
            )}
            {th.protected && (
              <span className="flex items-center gap-1 rounded-full border border-[#2a364b] bg-[#0d1420] px-2 py-0.5 text-[10px] font-medium text-[#8d9ab0]"><Lock size={9} /> Mitgeliefert</span>
            )}
          </div>
          {th.error && <p className="mt-0.5 font-mono text-[11px] text-rose-400">{th.error}</p>}
        </div>
      </div>

      <InstallLog lines={lines} phase={phase} failed={failed} />

      {!th.protected && (
        <div className="flex gap-2">
          <button onClick={() => run("update")} disabled={phase === "running"}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-[4px] border border-[#2a364b] bg-[#172133] py-1.5 text-xs font-medium text-[#69d7ff] transition-colors hover:bg-[#1b2536] disabled:opacity-40">
            <RefreshCw size={11} className={phase === "running" && action === "update" ? "animate-spin" : ""} />
            {phase === "running" && action === "update" ? "Aktualisiere …" : "Aktualisieren"}
          </button>
          <button onClick={() => run("uninstall")} disabled={phase === "running"}
            className="flex-1 rounded-[4px] border border-rose-500/20 bg-rose-500/10 py-1.5 text-xs font-medium text-rose-400 transition-colors hover:bg-rose-500/20 disabled:opacity-40">
            {phase === "running" && action === "uninstall" ? "Entferne …" : "Entfernen"}
          </button>
        </div>
      )}
    </div>
  )
}

export function AvailableThemeCockpitCard({ th, onRefresh }: { th: AvailableTheme; onRefresh: () => void }) {
  const [phase, setPhase] = useState<Phase>("idle")
  const [lines, setLines] = useState<string[]>([])
  const [failed, setFailed] = useState(false)
  const stopRef = useRef<(() => void) | null>(null)

  function handleInstall() {
    setPhase("running"); setLines([]); setFailed(false)
    stopRef.current = installTheme(th.id,
      (line) => setLines((l) => [...l.slice(-500), line]),
      () => { setPhase("done"); onRefresh() },
      (msg) => { setLines((l) => [...l, `[FEHLER] ${msg}`]); setFailed(true); setPhase("done") })
  }
  useEffect(() => () => stopRef.current?.(), [])

  return (
    <div className="flex flex-col gap-3 rounded-[6px] border border-[#2a364b] bg-[#111827] p-4">
      <div className="flex items-start gap-3">
        <div className="shrink-0 rounded-[4px] bg-[#1b2536] p-2 text-[#8d9ab0]"><Palette size={18} /></div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-[#e8eef8]">{th.name ?? th.id}</span>
            {th.name && th.name !== th.id && <span className="font-mono text-[10px] text-[#8d9ab0]">{th.id}</span>}
            <span className="rounded-full border border-[#2a364b] bg-[#0d1420] px-2 py-0.5 text-[10px] font-medium text-[#8d9ab0]">Verfügbar</span>
          </div>
        </div>
      </div>

      <InstallLog lines={lines} phase={phase} failed={failed} />

      <button onClick={handleInstall} disabled={phase === "running"}
        className="rounded-[4px] bg-violet-600 py-1.5 text-xs font-medium text-white transition-colors hover:bg-violet-500 disabled:opacity-40">
        {phase === "running" ? "Installiere …" : "Installieren"}
      </button>
    </div>
  )
}
