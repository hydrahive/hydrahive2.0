import { useTranslation } from "react-i18next"
import { AdminFeedback } from "@/features/cockpit/admin/ui"
import { DropResult } from "../DropProgress"
import { formatSize } from "../format"
import type { DeleteJob } from "./api"

/** Fortschritt bzw. Ergebnis eines Lösch-Auftrags – im Dialog und unter „Laufende Vorgänge“. */
export function DeleteProgress({ job }: { job: DeleteJob }) {
  const { t } = useTranslation("archive")
  if (job.kind === "drop_local" && (job.state === "failed" || job.state === "done")) return <DropResult job={job} />
  if (job.state === "failed") {
    return (
      <AdminFeedback tone="danger">
        <span className="block font-bold">{t(`delete.error.${job.error}`, { defaultValue: t("delete.error.unexpected") })}</span>
        <span className="block">{t("delete.nothing_deleted")}</span>
        {job.leftovers.length > 0 && <span className="mt-1 block break-all font-mono text-[11px]">{job.leftovers.join(", ")}</span>}
      </AdminFeedback>
    )
  }
  if (job.state === "done") {
    return (
      <AdminFeedback tone={job.leftovers.length ? "warning" : "success"}>
        <span className="block">{job.mode === "archive" ? t("delete.done_archive") : t("delete.done_permanent")}</span>
        {job.package && <span className="block break-all font-mono text-[11px]">{job.package}</span>}
        {job.leftovers.length > 0 && (
          <span className="mt-1 block">
            {t("delete.leftovers")} <span className="break-all font-mono text-[11px]">{job.leftovers.join(", ")}</span>
          </span>
        )}
      </AdminFeedback>
    )
  }
  const percent = job.bytes_total > 0 ? Math.min(100, Math.floor((job.bytes_done / job.bytes_total) * 100)) : 0
  const showBytes = (job.step === "pack" || job.step === "check") && job.bytes_total > 0
  return (
    <div className="space-y-2" data-delete-percent={percent}>
      <div className="flex justify-between text-xs text-[#8d9ab0]">
        <span>{t(`delete.step.${job.step}`)}</span>
        {showBytes && <span>{formatSize(job.bytes_done)} / {formatSize(job.bytes_total)} · {percent}%</span>}
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-[#172133]">
        <div className="h-full bg-[#69d7ff] transition-all" style={{ width: `${showBytes ? percent : 8}%` }} />
      </div>
    </div>
  )
}
