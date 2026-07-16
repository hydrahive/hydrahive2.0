import { TriangleAlert } from "lucide-react"
import type { ReactNode } from "react"
import { AdminAction } from "./AdminAction"
import { AdminDialog } from "./AdminDialog"
import type { AdminActionTone } from "./adminActionClass"

interface Props {
  title: ReactNode
  children: ReactNode
  confirmLabel: ReactNode
  cancelLabel: ReactNode
  onConfirm: () => void
  onClose: () => void
  busy?: boolean
  confirmTone?: Extract<AdminActionTone, "primary" | "danger">
}

export function AdminConfirmDialog({ title, children, confirmLabel, cancelLabel, onConfirm, onClose, busy = false, confirmTone = "danger" }: Props) {
  return (
    <AdminDialog
      eyebrow="Admin · Bestätigung"
      title={title}
      icon={<TriangleAlert size={16} />}
      onClose={busy ? undefined : onClose}
      maxWidthClass="max-w-md"
      footer={(
        <>
          <AdminAction onClick={onClose} disabled={busy}>{cancelLabel}</AdminAction>
          <AdminAction tone={confirmTone} onClick={onConfirm} disabled={busy}>{confirmLabel}</AdminAction>
        </>
      )}
    >
      <p className="text-sm leading-relaxed text-[#d4deeb]">{children}</p>
    </AdminDialog>
  )
}
