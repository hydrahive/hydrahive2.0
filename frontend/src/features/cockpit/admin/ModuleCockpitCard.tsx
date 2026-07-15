import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { ArrowUpCircle, Boxes, CheckCircle, RefreshCw, XCircle } from "lucide-react"
import type { ModuleEntry } from "@/features/modules/types"
import { installModule, uninstallModule, updateModule } from "@/features/modules/api"

type Phase = "idle" | "running" | "done"
type Action = "install" | "update" | "uninstall"

interface Props {
  mod: ModuleEntry
  onRefresh: () => void
}

/** Modul-Karte im Cockpit-Design (Pendant zu features/modules/ModuleCard,
 *  ohne box/zinc — nutzt dieselbe Stream-API). */
export function ModuleCockpitCard({ mod, onRefresh }: Props) {
  const { t } = useTranslation("modules")
  const [phase, setPhase] = useState<Phase>("idle")
  const [action, setAction] = useState<Action>("install")
  const [lines, setLines] = useState<string[]>([])
  const [failed, setFailed] = useState(false)
  const logRef = useRef<HTMLDivElement>(null)
  const stopRef = useRef<(() => void) | null>(null)

  useEffect(() => { logRef.current?.scrollTo(0, logRef.current.scrollHeight) }, [lines])
  useEffect(() => () => stopRef.current?.(), [])

  function run(a: Action) {
    setAction(a); setPhase("running"); setLines([]); setFailed(false)
    const fn = a === "install" ? installModule : a === "update" ? updateModule : uninstallModule
    stopRef.current = fn(
      mod.id,
      (line) => setLines((l) => [...l.slice(-500), line]),
      () => { setPhase("done"); onRefresh() },
      (msg) => { setLines((l) => [...l, `[FEHLER] ${msg}`]); setFailed(true); setPhase("done") },
    )
  }

  const busy = phase === "running"

  return (
    <div className="flex flex-col gap-3 rounded-[6px] border border-[#2a364b] bg-[#111827] p-4">
      <div className="flex items-start gap-3">
        <div className={"shrink-0 rounded-[4px] p-2 " + (mod.installed ? "bg-emerald-500/10 text-emerald-400" : "bg-[#1b2536] text-[#8d9ab0]")}>
          <Boxes size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-[#e8eef8]">{mod.name}</span>
            <span className="font-mono text-[10px] text-[#8d9ab0]">{mod.id}</span>
            {mod.version && (
              <span className="rounded-full border border-[#2a364b] bg-[#0d1420] px-1.5 py-0.5 text-[10px] text-[#8d9ab0]">v{mod.version}</span>
            )}
            {mod.update_available && mod.available_version && (
              <span title={t("update.available")} className="flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-300">
                <ArrowUpCircle size={9} />{t("update.badge", { from: mod.version, to: mod.available_version })}
              </span>
            )}
            {mod.installed && (mod.loaded ? (
              <span className="flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
                <CheckCircle size={9} /> {t("status.loaded")}
              </span>
            ) : (
              <span className="flex items-center gap-1 rounded-full border border-rose-500/30 bg-rose-500/15 px-2 py-0.5 text-[10px] font-medium text-rose-400">
                <XCircle size={9} /> {t("status.error")}
              </span>
            ))}
          </div>
          {mod.description && <p className="mt-1 text-[12px] leading-snug text-[#8d9ab0]">{mod.description}</p>}
          {mod.error && <p className="mt-0.5 font-mono text-[11px] text-rose-400">{mod.error}</p>}
        </div>
      </div>

      {phase !== "idle" && (
        <div ref={logRef} className="max-h-40 overflow-y-auto rounded-[4px] bg-[#0b111c] p-3 font-mono text-[11px] leading-relaxed">
          {lines.length === 0 && <span className="text-[#5b6675]">{t("log.waiting")}</span>}
          {lines.map((l, i) => (
            <div key={i} className={
              l.startsWith("[OK]") ? "text-emerald-400" :
              l.startsWith("[FEHLER]") || l.startsWith("[ERROR]") ? "text-rose-400" :
              l.startsWith("[WARN]") ? "text-amber-400" : "text-[#d7deea]"
            }>{l}</div>
          ))}
          {phase === "done" && (
            <div className={`mt-1 font-medium ${failed ? "text-rose-400" : "text-emerald-400"}`}>
              {failed ? t("log.failed") : t("log.success")}
            </div>
          )}
        </div>
      )}

      {mod.installed ? (
        <div className="flex gap-2">
          <button onClick={() => run("update")} disabled={busy}
            className={"flex flex-1 items-center justify-center gap-1.5 rounded-[4px] border py-1.5 text-xs font-medium transition-colors disabled:opacity-40 " +
              (mod.update_available ? "border-amber-500/30 bg-amber-500/15 text-amber-300 hover:bg-amber-500/25" : "border-[#2a364b] bg-[#172133] text-[#69d7ff] hover:bg-[#1b2536]")}>
            <RefreshCw size={11} className={busy && action === "update" ? "animate-spin" : ""} />
            {busy && action === "update" ? t("actions.updating") : mod.update_available ? t("update.available") : t("actions.update")}
          </button>
          <button onClick={() => run("uninstall")} disabled={busy}
            className="flex-1 rounded-[4px] border border-rose-500/20 bg-rose-500/10 py-1.5 text-xs font-medium text-rose-400 transition-colors hover:bg-rose-500/20 disabled:opacity-40">
            {busy && action === "uninstall" ? t("actions.uninstalling") : t("actions.uninstall")}
          </button>
        </div>
      ) : (
        <button onClick={() => run("install")} disabled={busy}
          className="rounded-[4px] bg-violet-600 py-1.5 text-xs font-medium text-white transition-colors hover:bg-violet-500 disabled:opacity-40">
          {busy && action === "install" ? t("actions.installing") : t("actions.install")}
        </button>
      )}
    </div>
  )
}
