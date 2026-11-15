import { useState } from "react"
import { Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { DeleteDialog } from "@/features/archive/delete/DeleteDialog"

interface Props {
  agentId: string
  agentName: string
  disabled?: boolean
  onDeleted: (agentId: string) => void
}

/**
 * Direkter 1–2-Klick-Weg zum Löschen eines Spezialisten aus der Team-Liste (Till 15.11.:
 * „wenn ich genau links neben mir mit einem oder 2 Klicks fertig sein könnte“). Öffnet sofort
 * den vorhandenen DeleteDialog (kind="agent", „Ins Archiv“ vorausgewählt) — kein Umweg über
 * das Bearbeiten-Overlay nötig. Nur für Admins sichtbar (siehe ProjectAgentsPanel), weil die
 * Lösch-Route `DELETE /api/agents/{id}` `require_admin` ist.
 *
 * `autoCloseOnDone`: Klick 1 = Papierkorb öffnet den Dialog, Klick 2 = „Ins Archiv starten“ —
 * danach schließt der Dialog sich selbst, sobald der Auftrag fertig ist (state "done"). Ohne
 * das wäre ein dritter Klick zum manuellen Schließen nötig, bevor der Agent aus der Liste
 * verschwindet (onDeleted feuert erst beim Schließen).
 */
export function ProjectAgentTrashButton({ agentId, agentName, disabled, onDeleted }: Props) {
  const { t } = useTranslation("agents")
  const [deleting, setDeleting] = useState(false)

  return (
    <>
      <button onClick={() => setDeleting(true)} disabled={disabled}
        className="rounded-[4px] p-1.5 text-[#9aa7bc] hover:bg-rose-500/15 hover:text-rose-300 disabled:cursor-not-allowed disabled:opacity-40"
        title={t("delete_specialist.button_for", { name: agentName })}>
        <Trash2 size={13} />
      </button>
      {deleting && (
        <DeleteDialog kind="agent" id={agentId} onClose={() => setDeleting(false)} onDeleted={() => onDeleted(agentId)}
          autoCloseOnDone />
      )}
    </>
  )
}
