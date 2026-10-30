import { useState } from "react"
import { Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminDialog, AdminFeedback, adminInputClass } from "@/features/cockpit/admin/ui"
import { archiveApi } from "./api"
import { formatSize } from "./format"

/** Muss zum Backend passen (routes/archive.py TRASH_CONFIRM_WORD). */
export const TRASH_CONFIRM_WORD = "Papierkorb"

interface Props {
  trashBytes: number
  onClose: () => void
  onDone: () => void
}

/** Papierkorb endgültig leeren – erst nach Eintippen des Bestätigungsworts. */
export function TrashConfirmDialog({ trashBytes, onClose, onDone }: Props) {
  const { t } = useTranslation("archive")
  const [typed, setTyped] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const ready = typed === TRASH_CONFIRM_WORD && !busy

  async function empty() {
    setBusy(true); setError(null)
    try { await archiveApi.emptyTrash(typed); onDone() }
    catch (err) { setError(err instanceof Error ? err.message : t("trash.failed")) }
    finally { setBusy(false) }
  }

  return (
    <AdminDialog
      eyebrow={t("title")}
      title={t("trash.title")}
      icon={<Trash2 size={15} />}
      onClose={onClose}
      maxWidthClass="max-w-md"
      footer={(
        <div className="flex justify-end gap-2">
          <AdminAction onClick={onClose}>{t("trash.cancel")}</AdminAction>
          <AdminAction tone="danger" disabled={!ready} onClick={() => void empty()}>
            <Trash2 size={11} /> {t("trash.confirm")}
          </AdminAction>
        </div>
      )}
    >
      <div className="space-y-3 p-4 text-sm text-[#e8eef8]">
        <p>{t("trash.text", { size: formatSize(trashBytes) })}</p>
        <label className="block space-y-1.5">
          <span className="text-xs text-[#9aa7bc]">{t("trash.type_word", { word: TRASH_CONFIRM_WORD })}</span>
          <input className={adminInputClass} value={typed} autoFocus
            onChange={(e) => setTyped(e.target.value)} placeholder={TRASH_CONFIRM_WORD} />
        </label>
        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
      </div>
    </AdminDialog>
  )
}
