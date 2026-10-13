import { useCallback, useEffect, useState } from "react"
import { RefreshCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminOverlay } from "@/features/cockpit/admin/AdminOverlay"
import { AdminAction } from "@/features/cockpit/admin/ui"
import { systemApi } from "@/features/system/api"
import { archiveApi, type ArchiveEntry, type ArchiveKind, type ArchiveStatus } from "./api"
import { ArchiveView } from "./ArchiveView"
import { TrashConfirmDialog } from "./TrashConfirmDialog"

/** Admin-Fenster „Archiv & Sicherung“ (docs/specs/archiv-system.md, Etappe 1). */
export function ArchiveOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("archive")
  const [status, setStatus] = useState<ArchiveStatus | null>(null)
  const [entries, setEntries] = useState<ArchiveEntry[]>([])
  const [kind, setKind] = useState<ArchiveKind | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [confirmTrash, setConfirmTrash] = useState(false)

  const reload = useCallback(async () => {
    try {
      const [s, e] = await Promise.all([archiveApi.status(), archiveApi.entries(kind)])
      setStatus(s); setEntries(e.entries); setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : t("load_failed"))
    }
  }, [kind, t])

  useEffect(() => {
    const first = setTimeout(() => { void reload() }, 0)
    return () => clearTimeout(first)
  }, [reload])

  async function setupSamba() {
    try { await systemApi.sambaSetup(); setError(null) }
    catch (err) { setError(err instanceof Error ? err.message : t("share.setup_failed")) }
  }

  return (
    <AdminOverlay
      eyebrow="Admin · Wartung"
      title={t("title")}
      onClose={onClose}
      maxWidthClass="max-w-4xl"
      headerActions={(
        <AdminAction tone="ghost" onClick={() => void reload()} aria-label={t("reload")} title={t("reload")}>
          <RefreshCw size={12} />
        </AdminAction>
      )}
    >
      <div className="space-y-3 p-4">
        <p className="text-sm text-[#8d9ab0]">{t("subtitle")}</p>
        <ArchiveView
          status={status}
          entries={entries}
          host={window.location.hostname}
          kind={kind}
          error={error}
          onKind={setKind}
          onEmptyTrash={() => setConfirmTrash(true)}
          onSetupSamba={() => void setupSamba()}
        />
      </div>
      {confirmTrash && status && (
        <TrashConfirmDialog
          trashBytes={status.storage.trash_bytes}
          onClose={() => setConfirmTrash(false)}
          onDone={() => { setConfirmTrash(false); void reload() }}
        />
      )}
    </AdminOverlay>
  )
}
