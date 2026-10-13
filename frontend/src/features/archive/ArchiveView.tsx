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
  onKind: (kind: ArchiveKind | null) => void
  onEmptyTrash: () => void
  onSetupSamba: () => void
}

/** Reine Ansicht des Admin-Fensters „Archiv & Sicherung“ (Spec archiv-system.md, Etappe 1). */
export function ArchiveView({ status, entries, host, kind, error, onKind, onEmptyTrash, onSetupSamba }: ArchiveViewProps) {
  return (
    <div className="space-y-3">
      {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
      {status && <ArchiveStorageSection storage={status.storage} onEmptyTrash={onEmptyTrash} />}
      {status && <ArchiveShareSection share={status.share} host={host} onSetupSamba={onSetupSamba} />}
      <ArchiveEntriesSection entries={entries} kind={kind} onKind={onKind} />
    </div>
  )
}
