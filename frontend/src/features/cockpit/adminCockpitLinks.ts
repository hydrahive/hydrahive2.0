import type { LucideIcon } from "lucide-react"
import { Archive, Boxes, Brain, CircuitBoard, Container, GitBranch, Globe, KeyRound, ListChecks, MonitorCog, MoonStar, Network, PlugZap, RefreshCw, Server, ShieldCheck, SlidersHorizontal, Users, WandSparkles } from "lucide-react"

/**
 * Einstiege der Admin-Cockpit-Startseite (Plan admin-cockpit-kompakt): jeder genau einmal.
 * `id` = Aktions-Kennung für OVERLAY_BY_ACTION (z. B. „users“ öffnet das Benutzer-Fenster).
 */
export interface AdminLink {
  id?: string
  title: string
  path: string
  icon: LucideIcon
  /** Kurzer Zusatz unter dem Namen (nur Verwaltung). */
  desc?: string
}

export const ADMIN_AREAS: AdminLink[] = [
  { id: "system", title: "System", path: "/system", icon: Server, desc: "Status, Netzwerk, Sicherung" },
  { id: "users", title: "Benutzer", path: "/users", icon: Users, desc: "Konten, Gruppen, API-Keys" },
  { title: "Freigaben", path: "/access", icon: ShieldCheck, desc: "Wer darf was nutzen" },
  { id: "modules", title: "Module", path: "/modules", icon: Boxes, desc: "Installieren und aktualisieren" },
  { id: "extensions", title: "Extensions", path: "/extensions", icon: GitBranch, desc: "Gitea und Docker-Dienste" },
  { id: "plugins", title: "Plugins", path: "/plugins", icon: PlugZap, desc: "Agent-Werkzeuge" },
  { id: "credentials", title: "Credentials", path: "/credentials", icon: KeyRound, desc: "Tokens und Schlüssel" },
  { id: "archive", title: "Archiv", path: "/archive", icon: Archive, desc: "Gelöschtes, Freigabe, NAS" },
]

export const OPS_LINKS: AdminLink[] = [
  { title: "LLM", path: "/llm", icon: Brain },
  { title: "MCP", path: "/mcp", icon: WandSparkles },
  { title: "Skills", path: "/skills", icon: SlidersHorizontal },
  { title: "VMs", path: "/vms", icon: MonitorCog },
  { title: "Container", path: "/containers", icon: Container },
  { title: "Compute-Nodes", path: "/nodes", icon: Network },
  { title: "Compute-Jobs", path: "/jobs", icon: ListChecks },
  { title: "Automationen", path: "/scheduled-tasks", icon: RefreshCw },
  { title: "Föderation", path: "/federation", icon: Globe },
  { title: "Zahnfee", path: "/zahnfee-config", icon: MoonStar },
  { title: "Globale Einstellungen", path: "/system/settings", icon: CircuitBoard },
]
