import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ListChecks, XCircle } from "lucide-react"
import { AdminDialog } from "@/features/cockpit/admin/ui/AdminDialog"
import { AdminAction } from "@/features/cockpit/admin/ui/AdminAction"
import { AdminFeedback } from "@/features/cockpit/admin/ui/AdminFeedback"
import { AdminConfirmDialog } from "@/features/cockpit/admin/ui/AdminConfirmDialog"
import { shortDateTime } from "@/features/nodes/format"
import { jobsApi } from "./api"
import { JobStatusBadge } from "./JobStatusBadge"
import { isCancellable } from "./types"
import type { ComputeJob, ComputeJobEvent } from "./types"

interface Props {
  job: ComputeJob
  onClose: () => void
  onChanged: () => void
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  if (value === null || value === undefined || value === "") return null
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-[#1c2637] py-1.5 last:border-0">
      <span className="text-[11px] uppercase tracking-wider text-[#5b6675]">{label}</span>
      <span className="min-w-0 truncate text-right text-sm text-[#d4deeb]">{value}</span>
    </div>
  )
}

function eventLabel(event: ComputeJobEvent, t: (k: string, o?: Record<string, unknown>) => string): string {
  if (event.event_type === "progress" && typeof event.data.progress === "number") {
    return t("event.progress", { progress: event.data.progress })
  }
  if (event.event_type === "failed" && event.data.error_code) {
    return t("event.error", { code: event.data.error_code })
  }
  if ((event.event_type === "requeued" || event.event_type === "expired") && event.data.reason) {
    return t("event.reason", { reason: event.data.reason })
  }
  return event.event_type
}

export function JobDetailDialog({ job, onClose, onChanged }: Props) {
  const { t } = useTranslation("jobs")
  const [events, setEvents] = useState<ComputeJobEvent[]>([])
  const [current, setCurrent] = useState<ComputeJob>(job)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [confirmCancel, setConfirmCancel] = useState(false)
  const [busy, setBusy] = useState(false)

  const refresh = useCallback(async () => {
    try {
      const [freshJob, freshEvents] = await Promise.all([
        jobsApi.get(job.job_id),
        jobsApi.events(job.job_id),
      ])
      setCurrent(freshJob)
      setEvents(freshEvents)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setLoading(false)
    }
  }, [job.job_id])

  useEffect(() => { void refresh() }, [refresh])

  const doCancel = async () => {
    setConfirmCancel(false)
    setBusy(true)
    setError(null)
    try {
      await jobsApi.cancel(job.job_id)
      await refresh()
      onChanged()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AdminDialog
      eyebrow="Admin"
      title={t("detail.title")}
      icon={<ListChecks size={16} />}
      onClose={onClose}
      maxWidthClass="max-w-2xl"
      footer={isCancellable(current.status)
        ? <AdminAction tone="danger" onClick={() => setConfirmCancel(true)} disabled={busy}>
            <XCircle size={12} className="mr-1 inline" />{busy ? t("detail.cancelling") : t("detail.cancel")}
          </AdminAction>
        : undefined}
    >
      <div className="space-y-5">
        <div className="flex items-center gap-2">
          <JobStatusBadge status={current.status} />
          <span className="rounded-[3px] border border-[#2a364b] bg-[#172133] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#8d9ab0]">
            {t(`resource_kind.${current.resource_kind}`, { defaultValue: current.resource_kind })}
          </span>
          <span className="font-mono text-sm text-[#e8eef8]">{current.operation}</span>
        </div>

        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}

        <div className="rounded-[6px] border border-[#2a364b] bg-[#111827] px-3">
          <Row label="ID" value={<span className="font-mono text-xs">{current.job_id}</span>} />
          <Row label={t("columns.node")} value={current.node_id} />
          <Row label={t("columns.resource")} value={current.resource_id ?? "–"} />
          <Row label={t("card.generation")} value={current.generation} />
          <Row label={t("columns.attempts")} value={current.attempts} />
          <Row label={t("columns.progress")} value={`${current.progress}%`} />
          {current.error_code && <Row label={t("card.error_code")} value={<span className="text-rose-300">{current.error_code}</span>} />}
          <Row label={t("card.created_by")} value={current.created_by} />
          <Row label={t("columns.created_at")} value={shortDateTime(current.created_at)} />
          <Row label={t("card.started_at")} value={shortDateTime(current.started_at)} />
          <Row label={t("card.finished_at")} value={shortDateTime(current.finished_at)} />
          <Row label={t("card.lease_until")} value={shortDateTime(current.lease_until)} />
        </div>

        <section>
          <h3 className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[#69d7ff]">{t("detail.timeline")}</h3>
          {loading ? (
            <AdminFeedback loading>{t("loading")}</AdminFeedback>
          ) : events.length === 0 ? (
            <p className="text-xs text-[#5b6675]">{t("detail.no_events")}</p>
          ) : (
            <ol className="space-y-1.5">
              {events.map((event) => (
                <li key={event.event_id} className="flex items-center gap-3 rounded-[4px] border border-[#1c2637] bg-[#0d1420] px-3 py-1.5">
                  <span className="font-mono text-[10px] text-[#5b6675]">{t("event.sequence", { sequence: event.sequence })}</span>
                  <span className="flex-1 text-xs text-[#d4deeb]">{eventLabel(event, t)}</span>
                  <span className="text-[10px] text-[#5b6675]">{shortDateTime(event.created_at)}</span>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>

      {confirmCancel && (
        <AdminConfirmDialog
          title={t("confirm.cancel_title")}
          confirmLabel={t("confirm.confirm")}
          cancelLabel={t("confirm.cancel")}
          confirmTone="danger"
          onConfirm={doCancel}
          onClose={() => setConfirmCancel(false)}
        >
          {t("confirm.cancel_body")}
        </AdminConfirmDialog>
      )}
    </AdminDialog>
  )
}
