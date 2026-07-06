import type { CSSProperties } from "react"
import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { ArrowUpCircle, Boxes, CheckCircle, RefreshCw, XCircle } from "lucide-react"
import { rgbFor } from "@/shared/colors"
import type { ModuleEntry } from "./types"
import { installModule, uninstallModule, updateModule } from "./api"

type Phase = "idle" | "running" | "done"
type Action = "install" | "update" | "uninstall"

interface Props {
  mod: ModuleEntry
  onRefresh: () => void
}

/** Eine Karte pro Modul — Buttons je nach Installationsstatus. */
export function ModuleCard({ mod, onRefresh }: Props) {
  const { t } = useTranslation("modules")
  const [phase, setPhase] = useState<Phase>("idle")
  const [action, setAction] = useState<Action>("install")
  const [lines, setLines] = useState<string[]>([])
  const [failed, setFailed] = useState(false)
  const logRef = useRef<HTMLDivElement>(null)
  const stopRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight)
  }, [lines])

  useEffect(() => () => stopRef.current?.(), [])

  function run(a: Action) {
    setAction(a)
    setPhase("running")
    setLines([])
    setFailed(false)
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
    <div className="box overflow-hidden flex flex-col gap-3 p-4" style={{ "--c": rgbFor("/plugins") } as CSSProperties}>
      <div className="flex items-start gap-3">
        <div className={
          "p-2 rounded-lg shrink-0 " +
          (mod.installed ? "bg-emerald-500/10 text-emerald-400" : "bg-zinc-700/50 text-zinc-400")
        }>
          <Boxes size={18} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-zinc-100 text-sm">{mod.name}</span>
            <span className="text-[10px] text-zinc-500 font-mono">{mod.id}</span>
            {mod.version && (
              <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-zinc-800 text-zinc-400 border border-white/[6%]">
                v{mod.version}
              </span>
            )}
            {mod.update_available && mod.available_version && (
              <span
                title={t("update.available")}
                className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/15 text-amber-300 border border-amber-500/30">
                <ArrowUpCircle size={9} />
                {t("update.badge", { from: mod.version, to: mod.available_version })}
              </span>
            )}
            {mod.installed && (
              mod.loaded ? (
                <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                  <CheckCircle size={9} /> {t("status.loaded")}
                </span>
              ) : (
                <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-rose-500/15 text-rose-400 border border-rose-500/30">
                  <XCircle size={9} /> {t("status.error")}
                </span>
              )
            )}
          </div>
          {mod.description && (
            <p className="text-[12px] text-zinc-400 mt-1 leading-snug">{mod.description}</p>
          )}
          {mod.error && (
            <p className="text-[11px] text-rose-400 mt-0.5 font-mono">{mod.error}</p>
          )}
        </div>
      </div>

      {phase !== "idle" && (
        <div ref={logRef}
          className="overflow-y-auto p-3 font-mono text-[11px] leading-relaxed bg-zinc-950/50 rounded-lg max-h-40">
          {lines.length === 0 && <span className="text-zinc-600">{t("log.waiting")}</span>}
          {lines.map((l, i) => (
            <div key={i} className={
              l.startsWith("[OK]") ? "text-emerald-400" :
              l.startsWith("[FEHLER]") || l.startsWith("[ERROR]") ? "text-rose-400" :
              l.startsWith("[WARN]") ? "text-amber-400" :
              "text-zinc-300"
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
          <button
            onClick={() => run("update")}
            disabled={busy}
            className={
              "flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg border text-xs font-medium transition-colors disabled:opacity-40 " +
              (mod.update_available
                ? "bg-amber-500/15 hover:bg-amber-500/25 border-amber-500/30 text-amber-300"
                : "bg-violet-500/10 hover:bg-violet-500/20 border-violet-500/20 text-violet-300")
            }>
            <RefreshCw size={11} className={busy && action === "update" ? "animate-spin" : ""} />
            {busy && action === "update"
              ? t("actions.updating")
              : mod.update_available ? t("update.available") : t("actions.update")}
          </button>
          <button
            onClick={() => run("uninstall")}
            disabled={busy}
            className="flex-1 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-rose-400 text-xs font-medium transition-colors disabled:opacity-40">
            {busy && action === "uninstall" ? t("actions.uninstalling") : t("actions.uninstall")}
          </button>
        </div>
      ) : (
        <button
          onClick={() => run("install")}
          disabled={busy}
          className="py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-medium transition-colors disabled:opacity-40">
          {busy && action === "install" ? t("actions.installing") : t("actions.install")}
        </button>
      )}
    </div>
  )
}
