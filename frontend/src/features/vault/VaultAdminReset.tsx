import { useState } from "react"
import { useTranslation } from "react-i18next"
import { LockKeyhole } from "lucide-react"
import { AdminAction, AdminConfirmDialog } from "@/features/cockpit/admin/ui"
import { resetVaultPin } from "./vaultActions"

/** Admin: Vault-PIN eines Nutzers entfernen (docs/specs/vault.md §4.4). Der Admin erfährt/setzt nie eine PIN. */
export function VaultAdminReset({ userId, username, onDone, onError }: {
  userId: string
  username: string
  onDone: (msg: string) => void
  onError: (msg: string) => void
}) {
  const { t } = useTranslation("vault")
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)

  async function confirm() {
    setBusy(true)
    try {
      await resetVaultPin(userId)
      onDone(t("admin_reset_done"))
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
      setOpen(false)
    }
  }

  return (
    <>
      <AdminAction tone="ghost" className="px-2" onClick={() => setOpen(true)} title={t("admin_reset")} aria-label={t("admin_reset")}>
        <LockKeyhole size={14} />
      </AdminAction>
      {open && (
        <AdminConfirmDialog title={t("admin_reset")} confirmLabel={t("admin_reset")} cancelLabel={t("cancel")}
          onConfirm={() => void confirm()} onClose={() => setOpen(false)} busy={busy}>
          {t("admin_reset_confirm", { name: username })}
        </AdminConfirmDialog>
      )}
    </>
  )
}
