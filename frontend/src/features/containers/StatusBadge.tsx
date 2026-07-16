import { useTranslation } from "react-i18next"
import { AdminStatus, type AdminStatusTone } from "@/features/cockpit/admin/ui"
import type { ActualState } from "./types"

const TONES: Record<ActualState, AdminStatusTone> = {
  created: "neutral",
  starting: "warning",
  running: "success",
  stopping: "warning",
  stopped: "neutral",
  error: "danger",
}

export function ContainerStatusBadge({ state }: { state: ActualState }) {
  const { t } = useTranslation("containers")
  const pending = state === "starting" || state === "stopping"
  return <AdminStatus tone={TONES[state]} dot pulse={pending}>{t(`status.${state}`)}</AdminStatus>
}
