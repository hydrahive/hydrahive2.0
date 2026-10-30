import { ArrowRightLeft, HardDrive, ShieldCheck } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminFeedback } from "@/features/cockpit/admin/ui"
import { cn } from "@/shared/cn"
import type { ArchiveLocation } from "./api"
import { formatSize } from "./format"

export interface MoveViewProps {
  locations: ArchiveLocation[]
  selected: string | null
  busy: boolean
  preparing: boolean
  error: string | null
  onSelect: (id: string) => void
  onMove: () => void
  onPrepare: () => void
}

/** Auswahl des neuen Archiv-Orts. Nur Platten aus der Liste – kein freies Pfadfeld (Spec Etappe 1b). */
export function MoveView({ locations, selected, busy, preparing, error, onSelect, onMove, onPrepare }: MoveViewProps) {
  const { t } = useTranslation("archive")
  const chosen = locations.find((l) => l.id === selected) ?? null
  const canMove = !!chosen && !chosen.current && chosen.problems.length === 0 && !busy
  const needsPrepare = !!chosen && chosen.kind === "disk" && chosen.problems.includes("target_not_writable")
  return (
    <div className="space-y-3 p-4 text-sm text-[#e8eef8]">
      <div className="space-y-2" role="radiogroup" aria-label={t("move.choose")}>
        {locations.map((l) => (
          <button
            key={l.id}
            type="button"
            role="radio"
            aria-checked={selected === l.id}
            data-archive-location={l.id}
            data-current={l.current ? "true" : "false"}
            disabled={l.current}
            onClick={() => onSelect(l.id)}
            className={cn(
              "flex w-full items-start gap-3 rounded-[4px] border p-3 text-left transition-colors disabled:cursor-default",
              selected === l.id ? "border-[#69d7ff]/60 bg-[#163248]" : "border-s-rand bg-s-innen hover:border-s-rand-hover",
            )}
          >
            <HardDrive size={16} className="mt-0.5 shrink-0 text-[#69d7ff]" />
            <span className="min-w-0 flex-1 space-y-0.5">
              <span className="block font-bold">
                {l.kind === "default" ? t("move.default_name") : l.mount}
                {l.current && <span className="ml-2 text-xs font-normal text-emerald-300">{t("move.current")}</span>}
              </span>
              <span className="block break-all font-mono text-xs text-[#9aa7bc]">{l.path}</span>
              <span className="block text-xs text-[#9aa7bc]">
                {t("move.free", { free: formatSize(l.free_bytes) })}
                {l.kind === "disk" && ` · ${l.device} · ${l.fstype}`}
              </span>
              {!l.current && l.problems.map((p) => (
                <span key={p} className="block text-xs text-amber-300">{t(`problem.${p}`)}</span>
              ))}
            </span>
          </button>
        ))}
      </div>
      {chosen && !chosen.current && <AdminFeedback>{t("move.explain")}</AdminFeedback>}
      {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
      <div className="flex flex-wrap justify-end gap-2">
        {needsPrepare && (
          <AdminAction data-archive-action="prepare-disk" disabled={preparing} onClick={onPrepare}>
            <ShieldCheck size={11} /> {preparing ? t("move.preparing") : t("move.prepare")}
          </AdminAction>
        )}
        <AdminAction tone="primary" data-archive-action="move-start" disabled={!canMove} onClick={onMove}>
          <ArrowRightLeft size={11} /> {t("move.start")}
        </AdminAction>
      </div>
    </div>
  )
}
