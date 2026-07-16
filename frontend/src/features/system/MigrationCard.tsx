import { useEffect, useState } from "react"
import { Loader2, Server } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminPanel, AdminStatus } from "@/features/cockpit/admin/ui"
import { systemApi } from "./api"
import { MigrationModal } from "./MigrationModal"

export function MigrationCard() {
  const { t } = useTranslation("system")
  const [open, setOpen] = useState(false)
  const [running, setRunning] = useState(false)

  useEffect(() => {
    let alive = true
    async function loadStatus() {
      try {
        const status = await systemApi.migrationStatus()
        if (alive) setRunning(status.running)
      } catch { /* ignore */ }
    }
    void loadStatus()
    return () => { alive = false }
  }, [open])

  return (
    <AdminPanel
      title={t("migration.title")}
      description={t("migration.description")}
      icon={Server}
      actions={running ? <AdminStatus tone="warning" dot>{t("migration.running_short")}</AdminStatus> : undefined}
      bodyClassName="space-y-3"
    >
      <AdminAction onClick={() => setOpen(true)} tone="primary">
        {running ? <Loader2 size={12} className="animate-spin" /> : <Server size={12} />}
        {running ? t("migration.running_short") : t("migration.open")}
      </AdminAction>
      {open && <MigrationModal onClose={() => setOpen(false)} />}
    </AdminPanel>
  )
}
