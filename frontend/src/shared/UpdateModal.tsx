import { useEffect, useRef, useState } from "react"
import { CheckCircle, Loader2, X, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"

export type UpdateState = "confirm" | "starting" | "running" | "done" | "failed"

interface Props {
  state: UpdateState
  newCommit?: string | null
  errorMessage?: string | null
  forceMode?: boolean
  onConfirm: () => void
  onClose: () => void
}

export function UpdateModal({ state, newCommit, errorMessage, forceMode, onConfirm, onClose }: Props) {
  const { t } = useTranslation("nav")
  const [logLines, setLogLines] = useState<string[]>([])
  const [logDisconnected, setLogDisconnected] = useState(false)
  const logRef = useRef<HTMLPreElement>(null)
  const isPolling = state === "starting" || state === "running"

  useEffect(() => {
    if (!isPolling && state !== "done" && state !== "failed") return
    let alive = true
    async function fetchLog() {
      try {
        const r = await api.get<{ lines: string[]; exists: boolean }>("/system/update/log?tail=300")
        if (!alive) return
        setLogDisconnected(false)
        if (r.exists) setLogLines(r.lines)
      } catch {
        if (!alive) return
        setLogDisconnected(true)
      }
    }
    fetchLog()
    const interval = isPolling ? 1500 : 0
    const t = interval ? setInterval(fetchLog, interval) : null
    return () => { alive = false; if (t) clearInterval(t) }
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
          <h2 className="text-lg font-bold text-white">{t("update.modal_title")}</h2>
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
                {t(forceMode ? "update.confirm_question_force" : "update.confirm_question")}
              </p>
              <p className="text-xs text-zinc-500 leading-relaxed">
                {t(forceMode ? "update.confirm_hint_force" : "update.confirm_hint")}
              </p>
            </>
          )}

          {(state === "starting" || state === "running") && (
            <div className="flex items-center gap-2 text-sm text-amber-300">
              <Loader2 size={14} className="animate-spin" />
              <span>{state === "starting" ? t("update.starting") : t("update.in_progress")}</span>
            </div>
          )}

          {state === "done" && (
            <div className="flex items-center gap-2 text-sm text-emerald-300">
              <CheckCircle size={14} />
              <span>{t("update.done", { commit: newCommit ?? "" })}</span>
            </div>
          )}

          {state === "failed" && (
            <div className="flex items-center gap-2 text-sm text-rose-300">
              <XCircle size={14} />
              <span>{t("update.failed", { error: errorMessage ?? "" })}</span>
            </div>
          )}

          {state !== "confirm" && (
            <div className="space-y-1.5">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">{t("update.log_title")}</p>
              <pre
                ref={logRef}
                className="rounded-lg border border-white/[6%] bg-zinc-950 p-3 text-[11px] font-mono leading-relaxed text-zinc-300 overflow-x-auto whitespace-pre-wrap min-h-[240px] max-h-[400px]"
              >
                {logLines.length > 0
                  ? logLines.join("")
                  : <span className="text-zinc-600">{t("update.log_empty")}</span>}
              </pre>
              {logDisconnected && (
                <p className="text-[11px] text-zinc-500 italic">{t("update.log_disconnected")}</p>
              )}
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
                {t("update.close")}
              </button>
              <button
                onClick={onConfirm}
                className="px-4 py-2 rounded-lg bg-gradient-to-r from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] hover:brightness-110 text-white text-sm font-medium shadow-md shadow-black/30"
              >
                {t("update.confirm_button")}
              </button>
            </>
          )}
          {(state === "done" || state === "failed") && (
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-gradient-to-r from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] hover:brightness-110 text-white text-sm font-medium shadow-md shadow-black/30"
            >
              {t("update.close")}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
