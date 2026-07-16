import { useCallback, useEffect, useMemo, useState } from "react"
import { Box, Play, Plus, RefreshCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import { HelpButton } from "@/i18n/HelpButton"
import type { Container } from "@/features/containers/types"
import { containersApi } from "@/features/containers/api"
import { ContainerCard } from "@/features/containers/ContainerCard"
import { CreateContainerDialog } from "@/features/containers/CreateContainerDialog"
import { EditContainerDialog } from "@/features/containers/EditContainerDialog"
import { CockpitButton } from "../CockpitButton"
import { AdminFeedback, AdminStat } from "./ui"
import { AdminOverlay } from "./AdminOverlay"
import { ContainerDetailOverlay } from "./ContainerDetailOverlay"

const POLL_MS = 4000

interface Props {
  onClose: () => void
  selectedContainerId?: string | null
  onSelectContainer?: (containerId: string | null) => void
}

export function ContainersOverlay({ onClose, selectedContainerId = null, onSelectContainer }: Props) {
  const { t } = useTranslation("containers")
  const [containers, setContainers] = useState<Container[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [editContainer, setEditContainer] = useState<Container | null>(null)

  const refresh = useCallback(async () => {
    try {
      const nextContainers = await containersApi.list()
      setContainers(nextContainers)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (selectedContainerId) return
    const initial = window.setTimeout(refresh, 0)
    const interval = window.setInterval(refresh, POLL_MS)
    return () => { window.clearTimeout(initial); window.clearInterval(interval) }
  }, [refresh, selectedContainerId])

  const summary = useMemo(() => ({
    total: containers.length,
    running: containers.filter((container) => container.actual_state === "running").length,
  }), [containers])

  return (
    <AdminOverlay
      eyebrow="Admin"
      title={t("title")}
      onClose={onClose}
      maxWidthClass="max-w-6xl"
      headerActions={(
        <div className="flex items-center gap-2">
          <HelpButton topic="containers" />
          <CockpitButton onClick={refresh} title={t("detail.refresh")} aria-label={t("detail.refresh")}>
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          </CockpitButton>
          <CockpitButton tone="primary" onClick={() => setShowCreate(true)}>
            <Plus size={13} className="mr-1 inline" />{t("detail.new")}
          </CockpitButton>
        </div>
      )}
    >
      {!selectedContainerId && (
      <div className="space-y-6">
        <p className="text-sm text-[#8d9ab0]">{t("detail.subtitle")}</p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <AdminStat icon={Box} label={t("summary.total")} value={summary.total} />
          <AdminStat icon={Play} label={t("summary.running")} value={summary.running} />
        </div>

        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
        {loading ? <AdminFeedback loading>{t("loading")}</AdminFeedback> : !error && containers.length === 0 ? (
          <div className="rounded-[6px] border border-[#2a364b] bg-[#111827] p-10 text-center">
            <Box size={28} className="mx-auto mb-3 text-[#5b6675]" />
            <p className="text-sm text-[#8d9ab0]">{t("empty")}</p>
            <p className="mt-2 text-xs text-[#5b6675]">{t("logs.tip")} <span className="text-[#69d7ff]">debian/12</span> ist gut für die meisten Dienste, <span className="text-[#69d7ff]">alpine/3.21</span> für Minimum-Footprint.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {containers.map((container) => (
              <ContainerCard
                key={container.container_id}
                container={container}
                onStart={async () => { await containersApi.start(container.container_id); await refresh() }}
                onStop={async () => { await containersApi.stop(container.container_id); await refresh() }}
                onRestart={async () => { await containersApi.restart(container.container_id); await refresh() }}
                onDelete={async () => { await containersApi.remove(container.container_id); await refresh() }}
                onEdit={() => setEditContainer(container)}
                onOpenDetail={() => onSelectContainer?.(container.container_id)}
              />
            ))}
          </div>
        )}
      </div>
      )}

      {showCreate && <CreateContainerDialog onClose={() => setShowCreate(false)} onCreated={refresh} />}
      {editContainer && (
        <EditContainerDialog container={editContainer} onClose={() => setEditContainer(null)}
          onSaved={async () => { setEditContainer(null); await refresh() }} />
      )}
      {selectedContainerId && <ContainerDetailOverlay containerId={selectedContainerId} onClose={() => onSelectContainer?.(null)} />}
    </AdminOverlay>
  )
}
