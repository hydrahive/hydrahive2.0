import { useState } from "react"
import { HardDriveDownload } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminDialog, AdminFeedback } from "@/features/cockpit/admin/ui"
import { archiveApi, type ArchiveRemote } from "./api"
import { formatSize, uncPath } from "./format"

/** Welche Pakete: einzelne Pfade oder alle, die geprüft auf dem Server liegen. */
export type DropSelection = { paths: string[]; bytes: number } | { all: true }

interface ViewProps {
  remote: ArchiveRemote
  count: number
  bytes: number
  busy: boolean
  error: string | null
  onConfirm: () => void
  onClose: () => void
}

function serverPath(r: ArchiveRemote): string {
  const sub = r.subdir.split("/").filter(Boolean).join("\\")
  return sub ? `${uncPath(r.host, r.share)}\\${sub}` : uncPath(r.host, r.share)
}

/** Dialog „Lokale Kopie löschen“ (Etappe 3b): wo die Kopie liegt, was frei wird – ohne Namen-Eintippen. */
export function DropLocalView({ remote, count, bytes, busy, error, onConfirm, onClose }: ViewProps) {
  const { t } = useTranslation("archive")
  return (
    <AdminDialog eyebrow={t("title")} title={t("drop.title")} icon={<HardDriveDownload size={15} />} onClose={onClose}
      maxWidthClass="max-w-md"
      footer={(
        <div className="flex justify-end gap-2">
          <AdminAction onClick={onClose}>{t("drop.cancel")}</AdminAction>
          <AdminAction tone="danger" data-drop-action="confirm" disabled={busy || count === 0} onClick={onConfirm}>
            <HardDriveDownload size={11} /> {t("drop.confirm")}
          </AdminAction>
        </div>
      )}>
      <div className="space-y-3 p-4 text-sm text-[#e8eef8]">
        <p>{t("drop.text", { count, size: formatSize(bytes) })}</p>
        <div className="space-y-1">
          <p className="text-xs text-[#9aa7bc]">{t("drop.where")}</p>
          <p className="break-all rounded-[4px] border border-s-rand bg-s-innen px-2 py-1.5 font-mono text-xs">
            {serverPath(remote)}
          </p>
        </div>
        <p className="text-xs leading-relaxed text-[#9aa7bc]">{t("drop.safety")}</p>
        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
      </div>
    </AdminDialog>
  )
}

/** Hülle: schickt den Auftrag ab; der Fortschritt steht danach unter „Laufende Vorgänge“. */
export function DropLocalDialog({ remote, selection, onClose, onStarted }: {
  remote: ArchiveRemote; selection: DropSelection; onClose: () => void; onStarted: () => void
}) {
  const { t } = useTranslation("archive")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const all = "all" in selection
  const count = all ? remote.droppable : selection.paths.length
  const bytes = all ? remote.droppable_bytes : selection.bytes

  async function confirm() {
    setBusy(true); setError(null)
    try {
      await archiveApi.dropLocal(all ? { all_verified: true } : { paths: selection.paths })
      onStarted()
    } catch (err) { setError(err instanceof Error ? err.message : t("drop.failed")) }
    finally { setBusy(false) }
  }

  return <DropLocalView remote={remote} count={count} bytes={bytes} busy={busy} error={error}
    onConfirm={() => void confirm()} onClose={onClose} />
}
