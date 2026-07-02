import type { ReactNode } from "react"
import type { DashboardSummary } from "./api"
import { StatsRow } from "./_StatsRow"
import { RecentSessions } from "./_RecentSessions"
import { ServersOverview } from "./_ServersOverview"
import { AgentsList } from "./_AgentsList"
import { HealthStrip } from "./_HealthStrip"
import { TokenAuditCard } from "./_TokenAuditCard"
import { TailscaleCard } from "@/features/system/TailscaleCard"
import { AgentLinkCard } from "@/features/system/AgentLinkCard"
import { MinimaxUsageCard } from "@/features/system/MinimaxUsageCard"

/** Ein anordbares Dashboard-Widget. `render` bekommt die geladenen Daten und
 *  gibt den Karten-Inhalt zurück. Reihenfolge + Sichtbarkeit werden pro Nutzer
 *  gespeichert (siehe useDashboardLayout). */
export interface DashboardWidget {
  id: string
  /** Anzeigename im Anpassen-Modus. */
  label: string
  render: (data: DashboardSummary) => ReactNode
}

/** Alle verfügbaren Widgets in ihrer Standard-Reihenfolge. Neue Widgets hier
 *  ergänzen — sie erscheinen automatisch (ans Ende, sichtbar) bei bestehenden
 *  Nutzern, weil useDashboardLayout unbekannte IDs anhängt. */
export const DASHBOARD_WIDGETS: DashboardWidget[] = [
  {
    id: "health",
    label: "System-Status",
    render: (d) => <HealthStrip health={d.health} />,
  },
  {
    id: "stats",
    label: "Kennzahlen",
    render: (d) => <StatsRow stats={d.stats} />,
  },
  {
    id: "token-audit",
    label: "Token-Verbrauch",
    render: () => <TokenAuditCard />,
  },
  {
    id: "connections",
    label: "Verbindungen (Tailscale / AgentLink)",
    render: () => (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <TailscaleCard />
        <AgentLinkCard />
      </div>
    ),
  },
  {
    id: "minimax",
    label: "MiniMax-Nutzung",
    render: () => <MinimaxUsageCard />,
  },
  {
    id: "sessions-agents",
    label: "Sessions & Agenten",
    render: (d) => (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <RecentSessions sessions={d.recent_sessions} />
        <AgentsList agents={d.agents} />
      </div>
    ),
  },
  {
    id: "servers",
    label: "Server-Übersicht",
    render: (d) => <ServersOverview servers={d.servers} />,
  },
]

/** Standard-Reihenfolge als ID-Liste (für den Storage-Default). */
export const DEFAULT_WIDGET_ORDER = DASHBOARD_WIDGETS.map((w) => w.id)

export function getWidget(id: string): DashboardWidget | undefined {
  return DASHBOARD_WIDGETS.find((w) => w.id === id)
}
