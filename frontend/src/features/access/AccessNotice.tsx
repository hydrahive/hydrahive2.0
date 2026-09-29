import { useEffect, useState } from "react"
import { ShieldAlert } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminFeedback } from "@/features/cockpit/admin/ui"
import { api } from "@/shared/api-client"

// Einmaliger Hinweis nach dem Update: Diese Funktionen sind jetzt nur für Admins
// (docs/specs/access-groups.md §11 Punkt 3). Verschwindet nach „Verstanden“
// oder sobald jede Funktion freigegeben ist.
export function AccessNotice({ onOpen }: { onOpen: () => void }) {
  const { t } = useTranslation("access")
  const [pending, setPending] = useState<string[]>([])

  useEffect(() => {
    let alive = true
    api.get<{ pending: string[] }>("/access/notice")
      .then((r) => { if (alive) setPending(r.pending) })
      .catch(() => {})
    return () => { alive = false }
  }, [])

  if (pending.length === 0) return null
  const ack = () => api.post<void>("/access/notice/ack", {}).then(() => setPending([])).catch(() => {})

  return (
    <AdminFeedback tone="warning">
      <div className="space-y-2">
        <p className="flex items-center gap-1.5 font-bold"><ShieldAlert size={13} />{t("notice.title")}</p>
        <p>{t("notice.text")}</p>
        <p className="font-mono text-[11px]">{pending.join(", ")}</p>
        <div className="flex gap-2">
          <AdminAction tone="primary" onClick={onOpen}>{t("notice.open")}</AdminAction>
          <AdminAction onClick={ack}>{t("notice.ack")}</AdminAction>
        </div>
      </div>
    </AdminFeedback>
  )
}
