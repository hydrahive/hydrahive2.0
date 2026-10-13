import { AdminFeedback } from "@/features/cockpit/admin/ui"
import type { ArchiveEntry, ArchiveKind, ArchiveStatus } from "./api"
import { ArchiveEntriesSection } from "./ArchiveEntriesSection"
import { ArchiveShareSection } from "./ArchiveShareSection"
import { ArchiveStorageSection } from "./ArchiveStorageSection"

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
}

/** Reine Ansicht des Admin-Fensters „Archiv & Sicherung“ (Spec archiv-system.md, Etappe 1). */
export function ArchiveView(props: ArchiveViewProps) {
  const { status, entries, host, kind, error, shareBusy, onKind, onEmptyTrash, onSetupSamba, onShareSwitch, onChangeLocation } = props
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
      <ArchiveEntriesSection entries={entries} kind={kind} onKind={onKind} />
    </div>
  )
}
