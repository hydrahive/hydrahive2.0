import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { DeleteDialog } from "@/features/archive/delete/DeleteDialog"
import type { Agent } from "@/features/agents/types"
import { CockpitButton } from "../CockpitButton"

interface Props {
  agent: Agent
  onDeleted: () => void
}

/**
 * Lösch-Abschnitt für Spezialisten im Projekt-Cockpit (Till 15.11.: „wieso kann ich sie
 * nicht auch in den Projekten links beim Editieren löschen?" — bisher ging Löschen nur
 * über Einstellungen → Agenten, eine „Klickorgie").
 *
 * Nur für Spezialisten: der Projekt-Agent gehört zum Projekt, sein Löschen läuft über
 * ProjectDetailsOverlay (Projekt löschen). Nur für Admins sichtbar, weil die Lösch-Route
 * `DELETE /api/agents/{id}` `require_admin` ist — ohne Admin-Rechte würde der Dialog
 * ohnehin nur mit einem 403 enden.
 */
export function ProjectAgentDeleteSection({ agent, onDeleted }: Props) {
  const { t } = useTranslation("agents")
  const isAdmin = useAuthStore((state) => state.role) === "admin"
  const [deleting, setDeleting] = useState(false)

  if (agent.type !== "specialist" || !isAdmin) return null

  return (
    <section className="mx-4 mb-3 shrink-0 rounded-[4px] border border-rose-500/30 bg-rose-500/[7%] p-3">
      <h3 className="text-sm font-semibold text-rose-200">{t("delete_specialist.title")}</h3>
      <p className="mt-1 text-xs leading-5 text-rose-200/70">{t("delete_specialist.hint")}</p>
      <div className="mt-2">
        <CockpitButton onClick={() => setDeleting(true)}>{t("delete_specialist.button")}</CockpitButton>
      </div>
      {deleting && (
        <DeleteDialog kind="agent" id={agent.id} onClose={() => setDeleting(false)} onDeleted={onDeleted} />
      )}
    </section>
  )
}
