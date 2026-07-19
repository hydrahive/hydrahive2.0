import { useTranslation } from "react-i18next"
import { AdminStatus, type AdminStatusTone } from "@/features/cockpit/admin/ui/AdminStatus"
import type { NodeStatus } from "./types"

const STATUS_TONE: Record<NodeStatus, AdminStatusTone> = {
  pending: "warning",
  online: "success",
  degraded: "warning",
  offline: "neutral",
  draining: "warning",
  disabled: "neutral",
  revoked: "danger",
}

export function nodeStatusTone(status: NodeStatus): AdminStatusTone {
  return STATUS_TONE[status] ?? "neutral"
}

/** A node is usable as a placement target only when fully online. */
export function isPlaceableStatus(status: NodeStatus): boolean {
  return status === "online"
}

export function NodeStatusBadge({ status, pulse = false }: { status: NodeStatus; pulse?: boolean }) {
  const { t } = useTranslation("nodes")
  const tone = nodeStatusTone(status)
  return (
    <AdminStatus tone={tone} dot pulse={pulse && status === "online"}>
      {t(`status.${status}`, { defaultValue: status })}
    </AdminStatus>
  )
}
