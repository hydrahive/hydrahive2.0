import { useState } from "react"
import { useTranslation } from "react-i18next"
import { AdminFeedback, AdminToggle } from "@/features/cockpit/admin/ui"
import { AreaAuditLog } from "@/features/agents/areas/AreaAuditLog"
import { CategoryApprovals } from "@/features/agents/areas/CategoryApprovals"
import { UnassignedTools } from "@/features/agents/areas/UnassignedTools"
import { useAreaCatalog } from "@/features/agents/areas/areasApi"
import { AdminOverlay } from "./AdminOverlay"
import { ADMIN_OVERLAY_THEME } from "@/shared/brand/boxThemes"

/** Admin-Reiter „Agenten-Rechte“ (/admin?section=agent-rights): Bereiche statt Tool-Listen. Besitzer-Freigabe und Projekt-Pool
 *  liegen dort, wo man sie ohnehin bearbeitet (Benutzer bearbeiten, Projekt-Einstellungen). */
export function AgentRightsOverlay({ onClose }: { onClose: () => void }) {
  const { t, i18n } = useTranslation("agents")
  const lang = i18n.language?.startsWith("en") ? "en" : "de"
  const { catalog, error } = useAreaCatalog()
  const [expert, setExpert] = useState(false)
  return (
    <AdminOverlay theme={ADMIN_OVERLAY_THEME["agent-rights"]} eyebrow="Admin" title={t("areas.page_title")} onClose={onClose} maxWidthClass="max-w-3xl">
      <div className="space-y-6">
        <p className="text-sm text-[#9aa7bc]">{t("areas.page_subtitle")}</p>
        <AdminToggle checked={expert} onChange={(e) => setExpert(e.target.checked)} label={t("areas.expert")} />
        <section className="space-y-2">
          <h3 className="text-sm font-bold text-[#e8eef8]">{t("areas.audit_title")}</h3>
          <AreaAuditLog lang={lang} expert={expert} />
        </section>
        {error && <AdminFeedback tone="danger">{t("areas.load_failed")}</AdminFeedback>}
        {catalog && <UnassignedTools tools={catalog.unassigned} />}
        <CategoryApprovals />
      </div>
    </AdminOverlay>
  )
}
