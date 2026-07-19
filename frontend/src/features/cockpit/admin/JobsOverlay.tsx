import { useCallback, useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { Activity, ListChecks, RefreshCw, XCircle } from "lucide-react"
import { HelpButton } from "@/i18n/HelpButton"
import { jobsApi } from "@/features/jobs/api"
import { JobStatusBadge } from "@/features/jobs/JobStatusBadge"
import { JobDetailDialog } from "@/features/jobs/JobDetailDialog"
import { ACTIVE_JOB_STATUSES } from "@/features/jobs/types"
import type { ComputeJob, JobStatus } from "@/features/jobs/types"
import { nodesApi } from "@/features/nodes/api"
import type { ComputeNode } from "@/features/nodes/types"
import { shortDateTime } from "@/features/nodes/format"
import { CockpitButton } from "../CockpitButton"
import { AdminFeedback, AdminStat } from "./ui"
import { adminInputClass } from "./ui/AdminField"
import { AdminOverlay } from "./AdminOverlay"

const POLL_MS = 5000
const JOB_STATUSES: JobStatus[] = ["queued", "leased", "running", "succeeded", "failed", "cancelled", "expired"]

export function JobsOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("jobs")
  const [jobs, setJobs] = useState<ComputeJob[]>([])
  const [nodes, setNodes] = useState<ComputeNode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [nodeFilter, setNodeFilter] = useState<string>("")
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [detailJob, setDetailJob] = useState<ComputeJob | null>(null)

  const refresh = useCallback(async () => {
    try {
      const found = await jobsApi.list({
        node_id: nodeFilter || undefined,
        status: (statusFilter as JobStatus) || undefined,
        limit: 200,
      })
      setJobs(found)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setLoading(false)
    }
  }, [nodeFilter, statusFilter])

  useEffect(() => {
    void refresh()
    const interval = window.setInterval(refresh, POLL_MS)
    return () => window.clearInterval(interval)
  }, [refresh])

  useEffect(() => {
    nodesApi.list().then(setNodes).catch(() => setNodes([]))
  }, [])

  const summary = useMemo(() => ({
    total: jobs.length,
    active: jobs.filter((j) => ACTIVE_JOB_STATUSES.includes(j.status)).length,
    failed: jobs.filter((j) => j.status === "failed" || j.status === "expired").length,
  }), [jobs])

  return (
    <AdminOverlay
      eyebrow="Admin"
      title={t("title")}
      onClose={onClose}
      maxWidthClass="max-w-6xl"
      headerActions={
        <div className="flex items-center gap-2">
          <HelpButton topic="jobs" />
          <CockpitButton onClick={refresh} title={t("refresh")} aria-label={t("refresh")}>
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          </CockpitButton>
        </div>
      }
    >
      <div className="space-y-6">
        <p className="text-sm text-[#8d9ab0]">{t("subtitle")}</p>

        <div className="grid grid-cols-3 gap-3">
          <AdminStat icon={ListChecks} label={t("summary.total")} value={summary.total} />
          <AdminStat icon={Activity} label={t("summary.active")} value={summary.active} />
          <AdminStat icon={XCircle} label={t("summary.failed")} value={summary.failed} />
        </div>

        <div className="flex flex-wrap gap-3">
          <label className="flex-1 min-w-[180px] space-y-1">
            <span className="block text-[10px] font-bold uppercase tracking-[0.12em] text-[#8d9ab0]">{t("filter.node")}</span>
            <select className={adminInputClass} value={nodeFilter} onChange={(e) => setNodeFilter(e.target.value)}>
              <option value="">{t("filter.all_nodes")}</option>
              {nodes.map((n) => <option key={n.node_id} value={n.node_id}>{n.name}</option>)}
            </select>
          </label>
          <label className="flex-1 min-w-[180px] space-y-1">
            <span className="block text-[10px] font-bold uppercase tracking-[0.12em] text-[#8d9ab0]">{t("filter.status")}</span>
            <select className={adminInputClass} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">{t("filter.all_states")}</option>
              {JOB_STATUSES.map((s) => <option key={s} value={s}>{t(`status.${s}`)}</option>)}
            </select>
          </label>
        </div>

        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}

        {loading ? (
          <AdminFeedback loading>{t("loading")}</AdminFeedback>
        ) : jobs.length === 0 ? (
          <div className="rounded-[6px] border border-[#2a364b] bg-[#111827] p-10 text-center">
            <ListChecks size={28} className="mx-auto mb-3 text-[#5b6675]" />
            <p className="text-sm text-[#8d9ab0]">{t("empty")}</p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-[6px] border border-[#2a364b]">
            <table className="w-full text-left text-sm">
              <thead className="bg-[#131b2a] text-[10px] uppercase tracking-wider text-[#5b6675]">
                <tr>
                  <th className="px-3 py-2 font-bold">{t("columns.operation")}</th>
                  <th className="px-3 py-2 font-bold">{t("columns.resource")}</th>
                  <th className="px-3 py-2 font-bold">{t("columns.node")}</th>
                  <th className="px-3 py-2 font-bold">{t("columns.status")}</th>
                  <th className="px-3 py-2 font-bold">{t("columns.created_at")}</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr
                    key={job.job_id}
                    onClick={() => setDetailJob(job)}
                    className="cursor-pointer border-t border-[#1c2637] hover:bg-[#141d2d]"
                  >
                    <td className="px-3 py-2">
                      <span className="font-mono text-xs text-[#e8eef8]">{job.operation}</span>
                      <span className="ml-2 rounded-[3px] border border-[#2a364b] bg-[#172133] px-1 py-0.5 text-[9px] uppercase text-[#8d9ab0]">
                        {t(`resource_kind.${job.resource_kind}`, { defaultValue: job.resource_kind })}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-[#8d9ab0]">{job.resource_id ?? "–"}</td>
                    <td className="px-3 py-2 text-[#8d9ab0]">{job.node_id}</td>
                    <td className="px-3 py-2"><JobStatusBadge status={job.status} /></td>
                    <td className="px-3 py-2 text-xs text-[#5b6675]">{shortDateTime(job.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {detailJob && (
        <JobDetailDialog
          job={detailJob}
          onClose={() => setDetailJob(null)}
          onChanged={refresh}
        />
      )}
    </AdminOverlay>
  )
}
