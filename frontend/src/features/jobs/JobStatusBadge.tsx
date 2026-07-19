import { useTranslation } from "react-i18next"
import { AdminStatus, type AdminStatusTone } from "@/features/cockpit/admin/ui/AdminStatus"
import type { JobStatus } from "./types"

const STATUS_TONE: Record<JobStatus, AdminStatusTone> = {
  queued: "neutral",
  leased: "warning",
  running: "warning",
  succeeded: "success",
  failed: "danger",
  cancelled: "neutral",
  expired: "danger",
}

export function jobStatusTone(status: JobStatus): AdminStatusTone {
  return STATUS_TONE[status] ?? "neutral"
}

export function JobStatusBadge({ status }: { status: JobStatus }) {
  const { t } = useTranslation("jobs")
  const tone = jobStatusTone(status)
  const pulse = status === "running" || status === "leased"
  return (
    <AdminStatus tone={tone} dot pulse={pulse}>
      {t(`status.${status}`, { defaultValue: status })}
    </AdminStatus>
  )
}
