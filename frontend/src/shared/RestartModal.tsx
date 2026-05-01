import { CheckCircle, Loader2, X, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"

export type RestartState = "confirm" | "starting" | "running" | "done" | "failed"

interface Props {
  state: RestartState
  errorMessage?: string | null
  onConfirm: () => void
  onClose: () => void
}

export function RestartModal({ state, errorMessage, onConfirm, onClose }: Props) {
  const { t } = useTranslation("nav")
  const dismissable = state === "confirm" || state === "done" || state === "failed"

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={() => dismissable && onClose()}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md mx-4 rounded-2xl border border-white/[8%] bg-zinc-900 shadow-2xl shadow-black/40 flex flex-col"
      >
        <div className="flex items-center justify-between p-5 border-b border-white/[6%]">
          <h2 className="text-lg font-bold text-white">{t("restart.modal_title")}</h2>
          {dismissable && (
            <button onClick={onClose} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
              <X size={16} />
            </button>
          )}
        </div>

        <div className="p-5 space-y-3">
          {state === "confirm" && (
            <>
              <p className="text-sm text-zinc-200">{t("restart.confirm_question")}</p>
              <p className="text-xs text-zinc-500 leading-relaxed">{t("restart.confirm_hint")}</p>
            </>
          )}
          {(state === "starting" || state === "running") && (
            <div className="flex items-center gap-2 text-sm text-amber-300">
              <Loader2 size={14} className="animate-spin" />
              <span>{state === "starting" ? t("restart.starting") : t("restart.in_progress")}</span>
            </div>
          )}
          {state === "done" && (
            <div className="flex items-center gap-2 text-sm text-emerald-300">
              <CheckCircle size={14} />
              <span>{t("restart.done")}</span>
            </div>
          )}
          {state === "failed" && (
            <div className="flex items-center gap-2 text-sm text-rose-300">
              <XCircle size={14} />
              <span>{t("restart.failed", { error: errorMessage ?? "" })}</span>
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
                {t("restart.close")}
              </button>
              <button
                onClick={onConfirm}
                className="px-4 py-2 rounded-lg bg-gradient-to-r from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] hover:brightness-110 text-white text-sm font-medium shadow-md shadow-black/30"
              >
                {t("restart.confirm_button")}
              </button>
            </>
          )}
          {(state === "done" || state === "failed") && (
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-gradient-to-r from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] hover:brightness-110 text-white text-sm font-medium shadow-md shadow-black/30"
            >
              {t("restart.close")}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
