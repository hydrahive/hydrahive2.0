import { useTranslation } from "react-i18next"
import { AdminFeedback } from "@/features/cockpit/admin/ui"
import type { ArchiveMove } from "./api"
import { formatSize } from "./format"

/** Fortschritt bzw. Ergebnis des letzten Archiv-Umzugs (Spec Etappe 1b). Ohne Umzug: nichts. */
export function MoveProgress({ move }: { move: ArchiveMove | undefined }) {
  const { t } = useTranslation("archive")
  if (!move) return null
  const r = move.running
  if (r) {
    const percent = r.total_bytes > 0 ? Math.floor((r.copied_bytes / r.total_bytes) * 100) : 0
    return (
      <div className="space-y-2" data-archive-move-percent={percent}>
        <div className="flex justify-between text-xs text-[#9aa7bc]">
          <span>{t(`move.state.${r.state}`)}</span>
          <span>{formatSize(r.copied_bytes)} / {formatSize(r.total_bytes)} · {percent} %</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-s-innen">
          <div className="h-full bg-[#69d7ff] transition-all" style={{ width: `${percent}%` }} />
        </div>
        <p className="break-all font-mono text-[11px] text-[#9aa7bc]">→ {r.target}</p>
      </div>
    )
  }
  const last = move.last
  if (!last) return null
  if (last.state === "failed") {
    return (
      <AdminFeedback tone="danger">
        {t(`move.error.${last.error}`, { defaultValue: t("move.error.unexpected") })}
        {last.detail && <span className="ml-1 font-mono">{last.detail}</span>}
      </AdminFeedback>
    )
  }
  return (
    <AdminFeedback tone="success">
      {t("move.done", { target: last.target })}
      {!!last.left_behind?.length && (
        <span className="mt-1 block">
          {t("move.left_behind")} <span className="font-mono">{last.left_behind.join(", ")}</span>
        </span>
      )}
    </AdminFeedback>
  )
}
