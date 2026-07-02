import type { ReactNode } from "react"
import { BuddyPage } from "@/features/buddy/BuddyPage"
import { ChatPage } from "@/features/chat/ChatPage"
import { ButlerPage } from "@/features/butler/ButlerPage"
import { TeamchatPage } from "@/features/teamchat/TeamchatPage"
import { CommunicationPage } from "@/features/communication/CommunicationPage"
import { MemoryPage } from "@/features/memory/MemoryPage"
import { SkillsPage } from "@/features/skills/SkillsPage"
import { VMsPage } from "@/features/vms/VMsPage"
import { DataminingPage } from "@/features/datamining/DataminingPage"
import { DashboardPage } from "@/features/dashboard/DashboardPage"
import { ContainersPage } from "@/features/containers/ContainersPage"
import { FederationPage } from "@/features/federation/FederationPage"
import { StreamingPage } from "@/features/streaming/StreamingPage"
import { McpPage } from "@/features/mcp/McpPage"
import { ZahnfeePage } from "@/features/zahnfee/ZahnfeePage"
import { AtelierPage } from "@/modules/atelier/AtelierPage"
import { TailscaleCard } from "@/features/system/TailscaleCard"
import { AgentLinkCard } from "@/features/system/AgentLinkCard"
import { MinimaxUsageCard } from "@/features/system/MinimaxUsageCard"
import { MenuBlock } from "./blocks/MenuBlock"
import { PageBlock } from "./blocks/PageBlock"

/** Ein einsetzbarer Baustein. `render` bekommt die Attribute des Platzhalter-Tags
 *  (z.B. <hh-chatbox height="70vh"/> → { height: "70vh" }) und gibt das echte
 *  React-Element zurück. Bausteine sind self-contained: sie holen ihre Daten
 *  selbst, brauchen keine Props von der Seite. */
export interface SlotBlock {
  /** Tag-Name ohne hh-Präfix, z.B. "chatbox". */
  name: string
  /** Menschliche Beschreibung (für Designer-Doku / Fehlermeldungen). */
  label: string
  render: (attrs: Record<string, string>) => ReactNode
}

/** Voll-höhige Seiten-Bausteine (Chat-artig, wollen h-full). */
const fullPage = (Comp: () => ReactNode) =>
  (attrs: Record<string, string>): ReactNode => <PageBlock attrs={attrs} full>{<Comp />}</PageBlock>

/** Natürlich hohe Seiten-Bausteine (Listen/Dashboards, scrollen selbst). */
const flowPage = (Comp: () => ReactNode) =>
  (attrs: Record<string, string>): ReactNode => <PageBlock attrs={attrs} full={false}>{<Comp />}</PageBlock>

/** Komplettes Baustein-Inventar. Damit lässt sich JEDE Grundseite in ein
 *  Template setzen — auch die, für die noch kein fertiges Template existiert. */
export const SLOT_BLOCKS: SlotBlock[] = [
  // Navigation
  { name: "menu", label: "Navigationsmenü (type=horizontal|vertical)", render: (a) => <MenuBlock attrs={a} /> },

  // Arbeiten (Chat-artig, volle Höhe)
  { name: "buddy", label: "Buddy-Chat", render: fullPage(BuddyPage) },
  { name: "chatbox", label: "Buddy-Chat (Alias)", render: fullPage(BuddyPage) },
  { name: "werkstatt", label: "Werkstatt (Chat)", render: fullPage(ChatPage) },
  { name: "teamchat", label: "Teamchat", render: fullPage(TeamchatPage) },
  { name: "communication", label: "Kommunikation", render: flowPage(CommunicationPage) },

  // Kreativ / Automation
  { name: "atelier", label: "Atelier (Bildgenerator)", render: flowPage(AtelierPage) },
  { name: "butler", label: "Butler (Automation)", render: fullPage(ButlerPage) },

  // Auswertung / Wissen
  { name: "dashboard", label: "Dashboard", render: flowPage(DashboardPage) },
  { name: "memory", label: "Gedächtnis", render: flowPage(MemoryPage) },
  { name: "skills", label: "Skills", render: flowPage(SkillsPage) },
  { name: "datamining", label: "Datamining", render: flowPage(DataminingPage) },

  // Infrastruktur
  { name: "vms", label: "VMs", render: flowPage(VMsPage) },
  { name: "containers", label: "Container", render: flowPage(ContainersPage) },
  { name: "federation", label: "Föderation", render: flowPage(FederationPage) },
  { name: "streaming", label: "Streaming", render: flowPage(StreamingPage) },
  { name: "mcp", label: "MCP-Server", render: flowPage(McpPage) },
  { name: "zahnfee", label: "Zahnfee", render: flowPage(ZahnfeePage) },

  // Kleine Status-Karten (self-contained)
  { name: "tailscale", label: "Tailscale-Status", render: () => <TailscaleCard /> },
  { name: "agentlink", label: "AgentLink-Status", render: () => <AgentLinkCard /> },
  { name: "minimax", label: "MiniMax-Nutzung", render: () => <MinimaxUsageCard /> },
]

export function getBlock(name: string): SlotBlock | undefined {
  return SLOT_BLOCKS.find((b) => b.name === name.toLowerCase())
}
