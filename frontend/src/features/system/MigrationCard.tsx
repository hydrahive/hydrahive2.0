import type { CSSProperties } from "react"
import { useEffect, useState } from "react"
import { Server, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { rgbFor } from "@/shared/colors"
import { systemApi } from "./api"
import { MigrationModal } from "./MigrationModal"

export function MigrationCard() {
  const { t } = useTranslation("system")
  const [open, setOpen] = useState(false)
  const [running, setRunning] = useState(false)

  useEffect(() => {
    let alive = true
    systemApi.migrationStatus()
      .then((s) => { if (alive) setRunning(s.running) })
      .catch(() => { /* ignore */ })
    return () => { alive = false }
  }, [open])

  return (
    <div className="box overflow-hidden p-4 space-y-3" style={{ "--c": rgbFor("/system") } as CSSProperties}>
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
          {t("migration.title")}
        </p>
        <p className="text-zinc-300 text-sm mt-1">{t("migration.description")}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <button onClick={() => setOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-500/10 border border-violet-500/25 text-violet-200 text-xs font-medium hover:bg-violet-500/20 transition-colors">
          {running ? <Loader2 size={12} className="animate-spin" /> : <Server size={12} />}
          {running ? t("migration.running_short") : t("migration.open")}
        </button>
      </div>
      {open && <MigrationModal onClose={() => setOpen(false)} />}
    </div>
  )
}
