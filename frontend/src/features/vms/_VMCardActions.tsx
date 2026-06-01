import { useTranslation } from "react-i18next"
import { Camera, FileText, Monitor, Pencil, Play, Power, Square, Trash2 } from "lucide-react"

interface Props {
  vmName: string
  busy: boolean
  running: boolean
  canStart: boolean
  transitioning: boolean
  onStart: () => void
  onStop: () => void
  onPoweroff: () => void
  onDelete: () => void
  onConsole: () => void
  onSnapshots: () => void
  onLogs: () => void
  onEdit: () => void
}

export function VMCardActions({
  busy, running, canStart, transitioning,
  onStart, onStop, onPoweroff, onDelete,
  onConsole, onSnapshots, onLogs, onEdit,
}: Props) {
  const { t } = useTranslation("vms")
  return (
    <div className="flex items-center gap-2 pt-1">
      {canStart && (
        <button disabled={busy || transitioning} onClick={onStart}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-200 disabled:opacity-40 transition-colors">
          <Play size={12} /> {t("actions.start")}
        </button>
      )}
      {running && (
        <>
          <button onClick={onConsole}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-violet-500/15 hover:bg-violet-500/25 border border-violet-500/30 text-violet-200 transition-colors"
            title={t("actions.console_title")}>
            <Monitor size={12} /> {t("actions.console")}
          </button>
          <button disabled={busy || transitioning} onClick={onStop}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-200 disabled:opacity-40 transition-colors"
            title={t("actions.stop_title")}>
            <Square size={12} /> {t("actions.stop")}
          </button>
          <button disabled={busy || transitioning} onClick={onPoweroff}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-rose-200 disabled:opacity-40 transition-colors"
            title={t("actions.poweroff_title")}>
            <Power size={12} /> {t("actions.poweroff")}
          </button>
        </>
      )}
      <div className="flex-1" />
      <button onClick={onLogs}
        className="flex items-center gap-1.5 p-1.5 rounded-lg text-xs text-zinc-500 hover:text-zinc-200 hover:bg-white/5 transition-colors"
        title={t("actions.logs_title")}>
        <FileText size={12} />
      </button>
      <button onClick={onSnapshots}
        className="flex items-center gap-1.5 p-1.5 rounded-lg text-xs text-zinc-500 hover:text-zinc-200 hover:bg-white/5 transition-colors"
        title={t("actions.snapshots_title")}>
        <Camera size={12} />
      </button>
      {!running && !transitioning && (
        <button onClick={onEdit}
          className="flex items-center gap-1.5 p-1.5 rounded-lg text-xs text-zinc-500 hover:text-violet-300 hover:bg-violet-500/10 transition-colors"
          title={t("actions.edit_title")}>
          <Pencil size={12} />
        </button>
      )}
      {!running && !transitioning && (
        <button disabled={busy} onClick={onDelete}
          className="flex items-center gap-1.5 p-1.5 rounded-lg text-xs text-zinc-500 hover:text-rose-300 hover:bg-rose-500/10 transition-colors"
          title={t("actions.delete_title")}>
          <Trash2 size={12} />
        </button>
      )}
    </div>
  )
}
