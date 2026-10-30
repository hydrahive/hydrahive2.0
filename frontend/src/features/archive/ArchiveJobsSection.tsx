import { Activity, CheckCircle2, ChevronRight, TriangleAlert, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminFeedback, AdminPanel } from "@/features/cockpit/admin/ui"
import { DeleteProgress } from "./delete/DeleteProgress"
import type { DeleteJob, DeleteJobs } from "./delete/api"
import { MoveProgress } from "./MoveProgress"
import type { ArchiveMove } from "./api"

/** „Laufende Vorgänge“: Lösch-Aufträge und Umzug mit Fortschritt und Fehlern (Spec archiv-system.md, Etappe 2). */
export function ArchiveJobsSection({ jobs, move }: { jobs: DeleteJobs | undefined; move: ArchiveMove | undefined }) {
  const { t } = useTranslation("archive")
  const running = jobs?.running ?? null
  const queued = jobs?.queued ?? []
  const done = jobs?.done ?? []
  const nothing = !running && queued.length === 0 && done.length === 0 && !move?.running
  return (
    <div data-archive-section="jobs">
      <AdminPanel title={t("jobs.title")} icon={Activity} bodyClassName="space-y-2">
        {nothing && <AdminFeedback>{t("jobs.empty")}</AdminFeedback>}
        {move?.running && <MoveProgress move={move} />}
        {running && <JobRow job={running} />}
        {queued.map((j) => <JobRow key={j.id} job={j} label={t("jobs.queued")} />)}
        {done.length > 0 && <p className="pt-1 text-[11px] font-bold uppercase tracking-wide text-[#6d7a90]">{t("jobs.recent")}</p>}
        {done.map((j) => <DoneRow key={j.id} job={j} />)}
      </AdminPanel>
    </div>
  )
}

function JobRow({ job, label }: { job: DeleteJob; label?: string }) {
  const { t } = useTranslation("archive")
  return (
    <div className="space-y-1.5 rounded-[4px] border border-s-rand bg-s-innen p-3" data-delete-job={job.id}
      data-delete-state={job.state}>
      <div className="flex flex-wrap items-baseline justify-between gap-2 text-xs">
        <span className="font-bold text-[#e8eef8]">{t(`delete.kind.${job.kind}`)}: {job.name}</span>
        <span className="text-[#9aa7bc]">{label ?? t(`jobs.mode.${job.mode}`)}</span>
      </div>
      {job.state !== "queued" && <DeleteProgress job={job} />}
    </div>
  )
}

/** Erledigter Auftrag: eine Zeile mit Ergebnis, Einzelheiten zum Aufklappen (Plan admin-reiter-archiv: 20 Aufträge
 *  mit allen Details machten den Reiter 3 Bildschirme lang). */
function DoneRow({ job }: { job: DeleteJob }) {
  const { t } = useTranslation("archive")
  const ergebnis = job.state === "failed" ? "failed" : job.leftovers.length ? "partial" : "done"
  const Symbol = { failed: XCircle, partial: TriangleAlert, done: CheckCircle2 }[ergebnis]
  const farbe = { failed: "text-rose-300", partial: "text-amber-300", done: "text-emerald-300" }[ergebnis]
  return (
    <details className="group rounded-[4px] border border-s-rand bg-s-innen" data-delete-job={job.id} data-delete-state={job.state}>
      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-2 gap-y-0.5 px-3 py-2 text-xs hover:bg-s-hebung">
        <ChevronRight size={12} className="shrink-0 text-[#9aa7bc] transition-transform group-open:rotate-90" />
        <Symbol size={13} className={`shrink-0 ${farbe}`} aria-hidden="true" />
        <span className="min-w-0 flex-1 truncate font-bold text-[#e8eef8]">{t(`delete.kind.${job.kind}`)}: {job.name}</span>
        {/* Schmal: Ergebnis in eigener Zeile unter dem Namen, damit der Name nicht abgeschnitten wird. */}
        <span className={`w-full pl-[42px] sm:w-auto sm:shrink-0 sm:pl-0 ${farbe}`} data-job-result={ergebnis}>
          {job.state === "failed"
            ? t(`delete.error.${job.error}`, { defaultValue: t("delete.error.unexpected") })
            : t(`jobs.mode.${job.mode}`)}
        </span>
      </summary>
      <div className="border-t border-s-rand p-3"><DeleteProgress job={job} /></div>
    </details>
  )
}
