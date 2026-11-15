import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { DeleteDialog } from "@/features/archive/delete/DeleteDialog"
import type { Agent } from "@/features/agents/types"
import { CockpitButton } from "../CockpitButton"

interface Props {
  agent: Agent
  onDeleted: () => void
  /**
   * Feuert, sobald der Lösch-Dialog geöffnet wird — ab dann sperrt das Overlay „Speichern“
   * (siehe ProjectAgentEditOverlay): Schließt der Nutzer den Dialog vor Auftragsende wieder
   * (ausdrücklich erlaubt, Auftrag läuft weiter), könnte ein PATCH sonst `status: "active"`
   * zurückschreiben und die Sperre aus dem Lösch-Auftrag aufheben. Bleibt bis zum Ende dieser
   * Overlay-Sitzung gesperrt — bei „doch nicht löschen“ hilft Schließen + neu öffnen.
   */
  onDeleteStarted: () => void
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
export function ProjectAgentDeleteSection({ agent, onDeleted, onDeleteStarted }: Props) {
  const { t } = useTranslation("agents")
  const isAdmin = useAuthStore((state) => state.role) === "admin"
  const [deleting, setDeleting] = useState(false)

  if (agent.type !== "specialist" || !isAdmin) return null

  function openDialog() {
    setDeleting(true)
    onDeleteStarted()
  }

  return (
    <section className="mx-4 mb-3 shrink-0 rounded-[4px] border border-rose-500/30 bg-rose-500/[7%] p-3">
      <h3 className="text-sm font-semibold text-rose-200">{t("delete_specialist.title")}</h3>
      <p className="mt-1 text-xs leading-5 text-rose-200/70">{t("delete_specialist.hint")}</p>
      <div className="mt-2">
        <CockpitButton onClick={openDialog}>{t("delete_specialist.button")}</CockpitButton>
      </div>
      {deleting && (
        <DeleteDialog kind="agent" id={agent.id} onClose={() => setDeleting(false)} onDeleted={onDeleted} />
      )}
    </section>
  )
}
