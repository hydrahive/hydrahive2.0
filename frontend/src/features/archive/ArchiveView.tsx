import { AdminFeedback } from "@/features/cockpit/admin/ui"
import type { ArchiveEntry, ArchiveKind, ArchiveStatus, OrphanScan } from "./api"
import type { ArchiveTab } from "./archiveTabs"
import { ArchiveEntriesSection } from "./ArchiveEntriesSection"
import { ArchiveJobsSection } from "./ArchiveJobsSection"
import { ArchiveShareSection } from "./ArchiveShareSection"
import { ArchiveStorageSection } from "./ArchiveStorageSection"
import { OrphansView } from "./OrphansSection"
import { RemoteView, type RemoteViewProps } from "./RemoteSection"

export interface ArchiveViewProps {
  /** Reiter (Plan admin-reiter-archiv): zeigt nur dessen Bereiche. */
  tab: ArchiveTab
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
  /** Bereich „Externer Server“ (Etappe 3) – ohne die Werte aus dem Status. */
  remote?: Omit<RemoteViewProps, "remote">
  orphans?: OrphanScan | null
  orphansBusy?: boolean
  onCleanupOrphans?: () => void
  /** Etappe 3b: lokale Kopie eines Pakets löschen. */
  onDropLocal?: (entry: ArchiveEntry) => void
}

/** Reine Ansicht des Admin-Fensters „Archiv & Sicherung“ (Spec archiv-system.md, Etappe 1 + 2), ein Reiter. */
export function ArchiveView(props: ArchiveViewProps) {
  const { tab, status, entries, host, kind, error, shareBusy, onKind, onEmptyTrash, onSetupSamba, onShareSwitch, onChangeLocation } = props
  const { orphans = null, orphansBusy = false, onCleanupOrphans = () => {} } = props
  return (
    <div className="space-y-3">
      {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
      {tab === "speicher" && status && (
        <>
          <ArchiveStorageSection storage={status.storage} move={status.move} onEmptyTrash={onEmptyTrash}
            onChangeLocation={onChangeLocation} />
          <ArchiveShareSection share={status.share} host={host} busy={shareBusy}
            onSetupSamba={onSetupSamba} onSwitch={onShareSwitch} />
          {status.remote && props.remote && <RemoteView remote={status.remote} {...props.remote} />}
        </>
      )}
      {tab === "vorgaenge" && status && (
        <>
          <ArchiveJobsSection jobs={status.jobs} move={status.move} />
          <OrphansView scan={orphans} busy={orphansBusy} onCleanup={onCleanupOrphans} />
        </>
      )}
      {tab === "inhalt" && (
        <ArchiveEntriesSection entries={entries} kind={kind} onKind={onKind}
          onDropLocal={status?.remote?.active ? props.onDropLocal : undefined} />
      )}
    </div>
  )
}
