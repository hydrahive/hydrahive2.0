// Knopf „Alle updaten“ plus Fortschritt und Ergebnis (docs/specs/modul-update-alle.md).
import { RefreshCw, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { parseUpdateAll } from "./updateAllProgress"
import type { UpdateAllState } from "./useUpdateAll"

interface Props {
  outdatedCount: number
  state: UpdateAllState
  onStart: () => void
  onDismiss: () => void
  buttonClass: string
}

/** Text auf dem Knopf während des Ablaufs. */
function runningLabel(t: (k: string, o?: Record<string, unknown>) => string, state: UpdateAllState): string {
  const p = state.progress ?? parseUpdateAll([], 0)
  if (p.phase === "build") return t("update.all_build")
  if (p.phase === "restart" || p.phase === "finished") return t("update.all_restart")
  return t("update.all_running", { done: p.done, total: p.total })
}

export function UpdateAllButton({ outdatedCount, state, onStart, buttonClass }: Omit<Props, "onDismiss">) {
  const { t } = useTranslation("modules")
  if (outdatedCount === 0 && !state.running) return null
  return (
    <button type="button" onClick={onStart} disabled={state.running} className={buttonClass}>
      <RefreshCw size={12} className={state.running ? "animate-spin" : ""} />
      {state.running ? runningLabel(t, state) : t("update.all")}
    </button>
  )
}

/** Ergebnis nach dem Ablauf: was geklappt hat, was nicht (mit Grund). */
export function UpdateAllResult({ state, onDismiss }: Pick<Props, "state" | "onDismiss">) {
  const { t } = useTranslation("modules")
  const p = state.progress
  if (state.running || (!p && !state.error)) return null
  const failed = p?.failed ?? []
  const okCount = p?.ok.length ?? 0
  const summary = state.error && okCount === 0
    ? state.error
    : p?.upToDate ? t("update.all_uptodate")
    : failed.length ? t("update.all_done_failed", { ok: okCount, failed: failed.length })
    : t("update.all_done", { count: okCount })
  const bad = Boolean(state.error) || failed.length > 0
  return (
    <div role="status" data-update-all-result="1"
      className={`rounded-[6px] border p-3 text-sm ${bad ? "border-rose-500/30 bg-rose-500/10 text-rose-200" : "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"}`}>
      <div className="flex items-start justify-between gap-3">
        <p className="font-semibold">{summary}</p>
        <button type="button" onClick={onDismiss} aria-label={t("update.all_close")} className="rounded p-1 opacity-70 hover:opacity-100"><X size={14} /></button>
      </div>
      {failed.length > 0 && (
        <div className="mt-2">
          <p className="text-xs opacity-80">{t("update.all_failed_title")}</p>
          <ul className="mt-1 space-y-0.5 text-xs">
            {failed.map((f) => <li key={f.id}><span className="font-mono">{f.id}</span> – {f.reason}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}
