import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { RefreshCw, Settings } from "lucide-react"

interface Props {
  version: string | null
  commit: string | null
  updateBehind: number | null
  isAdmin: boolean
  onUpdateClick: () => void
}

export function AppFooter({ version, commit, updateBehind, isAdmin, onUpdateClick }: Props) {
  const { t } = useTranslation("nav")
  return (
    <footer className="flex items-center justify-between gap-3 px-4 py-1.5 border-t border-white/[6%] bg-zinc-950/80 text-[11px] text-zinc-500">
      <div className="flex items-center gap-3">
        <Link to="/system" className="flex items-center gap-1 hover:text-zinc-300">
          <Settings size={11} /> {t("items.system")}
        </Link>
        <span className="hidden sm:inline">·</span>
        <span className="hidden sm:flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_5px_rgba(52,211,153,0.65)]" />
          {t("online")}
        </span>
      </div>
      <div className="flex items-center gap-2 font-mono tabular-nums">
        {version && (
          <span>v{version}{commit && <> · <span className="text-zinc-600">{commit}</span></>}</span>
        )}
        {updateBehind !== null && (
          updateBehind > 0 ? (
            isAdmin ? (
              <button
                type="button"
                onClick={onUpdateClick}
                title={t("update.available")}
                className="px-1.5 py-0.5 rounded bg-amber-500/15 border border-amber-500/30 text-amber-300 hover:bg-amber-500/25"
              >
                ↑
              </button>
            ) : (
              <span
                title={t("update.available")}
                className="px-1.5 py-0.5 rounded bg-amber-500/15 border border-amber-500/30 text-amber-300"
              >
                ↑
              </span>
            )
          ) : (
            isAdmin && (
              <button
                type="button"
                onClick={onUpdateClick}
                title={t("update.force")}
                className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5"
              >
                <RefreshCw size={11} />
              </button>
            )
          )
        )}
      </div>
    </footer>
  )
}
