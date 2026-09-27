import type { ComponentType } from "react"
import { moduleBuddyWidgets } from "@/modules/index.generated"
import type { BuddyMediaWidgetProps } from "@/modules/types"

type BuddyWidget = ComponentType<BuddyMediaWidgetProps>

// Module exportieren `buddyWidgets` als bloße Komponenten (Aufgaben, Akte,
// Spiele …). Nur echte Funktionen übernehmen — ein kaputter Export darf den
// Buddy nicht abstürzen lassen. Seit 35627cdc wurden sie nicht mehr gerendert.
const BUDDY_WIDGETS: BuddyWidget[] = moduleBuddyWidgets.filter(
  (value): value is BuddyWidget => typeof value === "function",
)

/**
 * Rendert die Buddy-Kacheln installierter Module.
 * onPrompt feuert nur auf einen expliziten Klick im Widget (Offline-First-Spec).
 */
export function BuddyModuleWidgets({ onPrompt, projectId }: BuddyMediaWidgetProps) {
  if (BUDDY_WIDGETS.length === 0) return null
  return (
    <div className="my-[10px] space-y-[10px]">
      {BUDDY_WIDGETS.map((Widget, index) => (
        <Widget key={Widget.displayName || Widget.name || index} onPrompt={onPrompt} projectId={projectId} />
      ))}
    </div>
  )
}
