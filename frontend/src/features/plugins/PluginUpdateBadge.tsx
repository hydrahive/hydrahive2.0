// Plakette „v0.1.1 → v0.2.0“ bzw. „Neustart nötig“ (docs/specs/plugin-updates.md) – für Cockpit und alte Seite.
import { ArrowUpCircle, RotateCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import { updateBadge } from "./pluginUpdates"
import type { InstalledPlugin } from "./types"

export function PluginUpdateBadge({ plugin }: { plugin: InstalledPlugin }) {
  const { t } = useTranslation("plugins")
  const badge = updateBadge(plugin)
  if (!badge) return null
  if (badge.kind === "restart") {
    return (
      <span title={t("restart_needed_hint")} className="flex w-fit items-center gap-1 rounded-full border border-sky-500/30 bg-sky-500/15 px-2 py-0.5 text-[10px] font-medium text-sky-300">
        <RotateCw size={9} />{t("restart_needed")}
      </span>
    )
  }
  return (
    <span title={t("update_available")} className="flex w-fit items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-300">
      <ArrowUpCircle size={9} />{t("update_badge", { from: badge.from, to: badge.to })}
    </span>
  )
}
