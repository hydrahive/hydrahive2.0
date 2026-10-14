import { AdminFeedback } from "@/features/cockpit/admin/ui"
import type { ArchiveEntry, ArchiveKind, ArchiveStatus, OrphanScan } from "./api"
import { ArchiveEntriesSection } from "./ArchiveEntriesSection"
import { ArchiveJobsSection } from "./ArchiveJobsSection"
import { ArchiveShareSection } from "./ArchiveShareSection"
import { ArchiveStorageSection } from "./ArchiveStorageSection"
import { OrphansView } from "./OrphansSection"

export interface ArchiveViewProps {
  status: ArchiveStatus | null
  entries: ArchiveEntry[]
  host: string
  kind: ArchiveKind | null
  error: string | null
  shareBusy: boolean
  onKind: (kind: ArchiveKind | null) => void
  onEmptyTrash: () => void
  onSetupSamba: () => void
  onShareSwitch: (enabled: boolean) => void
  onChangeLocation: () => void
  orphans?: OrphanScan | null
  orphansBusy?: boolean
  onCleanupOrphans?: () => void
}

/** Reine Ansicht des Admin-Fensters „Archiv & Sicherung“ (Spec archiv-system.md, Etappe 1 + 2). */
export function ArchiveView(props: ArchiveViewProps) {
  const { status, entries, host, kind, error, shareBusy, onKind, onEmptyTrash, onSetupSamba, onShareSwitch, onChangeLocation } = props
  const { orphans = null, orphansBusy = false, onCleanupOrphans = () => {} } = props
  return (
    <div className="space-y-3">
      {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
      {status && (
        <ArchiveStorageSection storage={status.storage} move={status.move} onEmptyTrash={onEmptyTrash}
          onChangeLocation={onChangeLocation} />
      )}
      {status && (
        <ArchiveShareSection share={status.share} host={host} busy={shareBusy}
          onSetupSamba={onSetupSamba} onSwitch={onShareSwitch} />
      )}
      {status && <ArchiveJobsSection jobs={status.jobs} move={status.move} />}
      {status && <OrphansView scan={orphans} busy={orphansBusy} onCleanup={onCleanupOrphans} />}
      <ArchiveEntriesSection entries={entries} kind={kind} onKind={onKind} />
    </div>
  )
}
