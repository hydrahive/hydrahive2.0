import { useTranslation } from "react-i18next"
import { AdminFeedback } from "@/features/cockpit/admin/ui"
import type { DeleteJob } from "./delete/api"
import { formatSize } from "./format"

/** Ergebnis von „Lokale Kopie löschen“ (Etappe 3b): gelöscht + frei gewordener Platz, behaltene Pakete mit Grund. */
export function DropResult({ job }: { job: DeleteJob }) {
  const { t } = useTranslation("archive")
  const done = job.done_paths ?? []
  const kept = job.kept ?? []
  const failed = job.state === "failed"
  const tone = failed ? "danger" : kept.length ? "warning" : "success"
  return (
    <AdminFeedback tone={tone}>
      {failed && (
        <span className="block font-bold">{t(`drop.error.${job.error}`, { defaultValue: t("delete.error.unexpected") })}</span>
      )}
      {done.length > 0 || !failed
        ? <span className="block">{t("drop.done", { count: done.length, size: formatSize(job.freed_bytes ?? 0) })}</span>
        : <span className="block">{t("delete.nothing_deleted")}</span>}
      {kept.length > 0 && (
        <span className="mt-1 block">
          {t("drop.kept_title")}
          {kept.map((k) => (
            <span key={k.path} className="block">
              <span className="break-all font-mono text-[11px]">{k.path}</span>
              {" – "}{t(`drop.kept.${k.reason}`, { defaultValue: t("drop.kept.unexpected") })}
            </span>
          ))}
        </span>
      )}
    </AdminFeedback>
  )
}
