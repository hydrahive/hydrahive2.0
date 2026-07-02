import type { ReactNode } from "react"
import { TailscaleCard } from "@/features/system/TailscaleCard"
import { AgentLinkCard } from "@/features/system/AgentLinkCard"
import { MinimaxUsageCard } from "@/features/system/MinimaxUsageCard"

/** Ein einsetzbarer Baustein. `render` bekommt die Attribute des Platzhalter-Tags
 *  (z.B. <hh-chatbox agent="buddy"/> → { agent: "buddy" }) und gibt das echte
 *  React-Element zurück. Bausteine sind self-contained: sie holen ihre Daten
 *  selbst, brauchen keine Props von der Seite. */
export interface SlotBlock {
  /** Tag-Name ohne hh-Präfix, z.B. "chatbox". */
  name: string
  /** Menschliche Beschreibung (für Designer-Doku / Fehlermeldungen). */
  label: string
  render: (attrs: Record<string, string>) => ReactNode
}

/** Proof-Katalog v1 — bewusst self-contained Karten, die schon überall laufen.
 *  Später kommen hier hh-menu, hh-chatbox, hh-videoeditor etc. dazu. */
export const SLOT_BLOCKS: SlotBlock[] = [
  {
    name: "tailscale",
    label: "Tailscale-Status",
    render: () => <TailscaleCard />,
  },
  {
    name: "agentlink",
    label: "AgentLink-Status",
    render: () => <AgentLinkCard />,
  },
  {
    name: "minimax",
    label: "MiniMax-Nutzung",
    render: () => <MinimaxUsageCard />,
  },
]

export function getBlock(name: string): SlotBlock | undefined {
  return SLOT_BLOCKS.find((b) => b.name === name.toLowerCase())
}
