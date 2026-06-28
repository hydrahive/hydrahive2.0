import { AgentLinkCard } from "@/features/system/AgentLinkCard"
import { TailscaleCard } from "@/features/system/TailscaleCard"
import { SambaCard } from "@/features/system/SambaCard"

/**
 * Tab-Inhalte der Gruppe "Verbindungen". Jede Karteikarte zeigt genau die
 * thematisch passende(n) System-Card(s) — props-frei, daher direkt platzierbar.
 * (Mail-Settings liegen in den globalen Settings-Werten, Gruppe "Mail".)
 */
export function ConnTailscale() {
  return <div className="space-y-4"><TailscaleCard /></div>
}

export function ConnAgentLink() {
  return <div className="space-y-4"><AgentLinkCard /></div>
}

export function ConnSamba() {
  return <div className="space-y-4"><SambaCard /></div>
}
