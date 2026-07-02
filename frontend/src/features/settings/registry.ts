import { lazy, type LazyExoticComponent, type ComponentType } from "react"
import {
  Bot, FolderKanban, MessageCircle, Workflow, MoonStar, Sparkles, Server,
  Puzzle, Globe, Cpu, Package, Boxes, Palette, Users, Key,
  SlidersHorizontal, Database, Network, type LucideIcon,
} from "lucide-react"

// Lazy-geladene bestehende Feature-Pages, die direkt eingebettet werden.
// Code-split: nur geladen, wenn die Gruppe geöffnet wird.
const LlmPage = lazy(() => import("@/features/llm/LlmPage").then((m) => ({ default: m.LlmPage })))
const CredentialsPage = lazy(() => import("@/features/credentials/CredentialsPage").then((m) => ({ default: m.CredentialsPage })))
const SkillsPage = lazy(() => import("@/features/skills/SkillsPage").then((m) => ({ default: m.SkillsPage })))
const UsersPage = lazy(() => import("@/features/users/UsersPage").then((m) => ({ default: m.UsersPage })))
const SettingsPage = lazy(() => import("@/features/system/SettingsPage").then((m) => ({ default: m.SettingsPage })))
const ModulesPage = lazy(() => import("@/features/modules/ModulesPage").then((m) => ({ default: m.ModulesPage })))
const ThemesPage = lazy(() => import("@/features/themes/ThemesPage").then((m) => ({ default: m.ThemesPage })))
const ExtensionsPage = lazy(() => import("@/features/extensions/ExtensionsPage").then((m) => ({ default: m.ExtensionsPage })))
const PluginsPage = lazy(() => import("@/features/plugins/PluginsPage").then((m) => ({ default: m.PluginsPage })))
const FederationPage = lazy(() => import("@/features/federation/FederationPage").then((m) => ({ default: m.FederationPage })))

// Per-Tab-Inhalte für Multi-Tab-Gruppen (Kommunikation, Verbindungen, System).
const CommDiscord = lazy(() => import("./tabs/CommunicationTabs").then((m) => ({ default: m.CommDiscord })))
const CommWhatsApp = lazy(() => import("./tabs/CommunicationTabs").then((m) => ({ default: m.CommWhatsApp })))
const CommMail = lazy(() => import("./tabs/CommunicationTabs").then((m) => ({ default: m.CommMail })))
const ConnTailscale = lazy(() => import("./tabs/ConnectionTabs").then((m) => ({ default: m.ConnTailscale })))
const ConnAgentLink = lazy(() => import("./tabs/ConnectionTabs").then((m) => ({ default: m.ConnAgentLink })))
const ConnSamba = lazy(() => import("./tabs/ConnectionTabs").then((m) => ({ default: m.ConnSamba })))
const SysBackup = lazy(() => import("./tabs/SystemTabs").then((m) => ({ default: m.SysBackup })))
const SysBridge = lazy(() => import("./tabs/SystemTabs").then((m) => ({ default: m.SysBridge })))
const SysStatus = lazy(() => import("./tabs/SystemTabs").then((m) => ({ default: m.SysStatus })))
const ZahnfeeConfig = lazy(() => import("@/features/zahnfee/ZahnfeeConfig").then((m) => ({ default: m.ZahnfeeConfig })))

// Detail-Komponente (Submenü-Schema): Agenten — zeigt Settings des gewählten Agenten.
const AgentSettings = lazy(() => import("./detail/AgentSettings").then((m) => ({ default: m.AgentSettings })))
const AgentSubMenu = lazy(() => import("./detail/AgentSubMenu").then((m) => ({ default: m.AgentSubMenu })))
const ProjectSettings = lazy(() => import("./detail/ProjectSettings").then((m) => ({ default: m.ProjectSettings })))
const ProjectSubMenu = lazy(() => import("./detail/ProjectSubMenu").then((m) => ({ default: m.ProjectSubMenu })))

// Noch nicht ins Schema migriert (Vollbild via EmbedFrame): MCP, Butler.
const McpPage = lazy(() => import("@/features/mcp/McpPage").then((m) => ({ default: m.McpPage })))
const ButlerPage = lazy(() => import("@/features/butler/ButlerPage").then((m) => ({ default: m.ButlerPage })))

/**
 * Settings-Gruppen-Registry (SSOT für die linke Auswahl-Spalte).
 *
 * Entstanden aus Tills Blueprint-Board "einstellungsseite": EINE zentrale
 * Settings-Seite, links die Hauptgruppen (logisch geordnet), Mitte der Inhalt
 * mit Karteikarten, rechts ein kontextabhängiges Submenü (das z.B. bei
 * "agenten" die Agenten listet) — wird ausgeblendet, wenn die Gruppe keins
 * braucht (hasSubmenu=false).
 *
 * WICHTIG (Tills Vorgabe): hier NUR Einstellungen — Auswertungen/Statistiken
 * bleiben auf den eigenen Feature-Seiten (z.B. Zahnfee-Auswertung getrennt vom
 * Zahnfee-Setting).
 *
 * `tabs` = die Karteikarten oben im Inhaltsbereich. `route` (optional) verlinkt
 * vorerst auf die bestehende Seite, solange der Inhalt noch nicht migriert ist
 * (Gerüst-Ansatz: Struktur steht, Inhalt zieht etappenweise nach).
 */
export interface SettingsGroup {
  id: string
  label: string
  icon: LucideIcon
  hasSubmenu: boolean
  submenuLabel?: string
  tabs: string[]
  route?: string          // bestehende Seite (Fallback-Link, bis eingebettet)
  // Direkt eingebettete Komponente. Wenn gesetzt, rendert ContentArea sie
  // (in einem isolierten Scroll-Container) statt Platzhalter + Link.
  component?: LazyExoticComponent<ComponentType>
  // Per-Tab-Komponenten (Tab-Name → Komponente) für Multi-Tab-Gruppen.
  // Hat Vorrang vor `component` für den jeweils aktiven Tab.
  tabComponents?: Record<string, LazyExoticComponent<ComponentType>>
  // Wenn true, wird die eingebettete component in einen EmbedFrame gepackt
  // (für Vollbild-Pages mit -m-/h-calc-Layout: Projekte, MCP, … solange noch
  // nicht ins Schema migriert).
  fullscreen?: boolean
  // Detail-Komponente für Gruppen MIT Submenü: bekommt die im Submenü gewählte
  // itemId und zeigt nur deren Einstellungen (Tills Schema). Hat Vorrang vor
  // component, wenn hasSubmenu=true.
  detailComponent?: LazyExoticComponent<ComponentType<{ itemId: string | null }>>
  // Eigene Submenü-Komponente (z.B. echte Agentenliste mit Farben) statt des
  // generischen SubMenu. Bekommt activeItem + onSelect.
  submenuComponent?: LazyExoticComponent<ComponentType<{ activeItem: string | null; onSelect: (id: string) => void }>>
  adminOnly?: boolean
}

export const SETTINGS_GROUPS: SettingsGroup[] = [
  // Agenten & Projekte bringen ihre eigene Liste+Detail-Ansicht (Vollbild) mit
  // — das ist bereits die ideale Settings-UI. Daher kein zusätzliches Submenü,
  // sondern ein klarer Verweis auf die vollwertige Seite (kein erzwungenes
  // Einbetten, das die bestehende Bedienung verschlechtern würde).
  { id: "agents", label: "Agenten", icon: Bot, hasSubmenu: true,
    submenuLabel: "Agenten", tabs: ["Einstellungen"], route: "/agents",
    detailComponent: AgentSettings, submenuComponent: AgentSubMenu },
  { id: "projects", label: "Projekte", icon: FolderKanban, hasSubmenu: true,
    submenuLabel: "Projekte", tabs: ["Einstellungen"], route: "/projects",
    detailComponent: ProjectSettings, submenuComponent: ProjectSubMenu },
  { id: "communication", label: "Kommunikation", icon: MessageCircle, hasSubmenu: false,
    tabs: ["Discord", "WhatsApp", "Mail"], route: "/communication",
    tabComponents: { Discord: CommDiscord, WhatsApp: CommWhatsApp, Mail: CommMail } },
  { id: "butler", label: "Butler", icon: Workflow, hasSubmenu: false,
    tabs: ["Flows"], route: "/butler", component: ButlerPage, fullscreen: true },
  { id: "zahnfee", label: "Zahnfee", icon: MoonStar, hasSubmenu: false,
    tabs: ["Einstellungen"], route: "/zahnfee", component: ZahnfeeConfig, adminOnly: true },
  { id: "skills", label: "Skills", icon: Sparkles, hasSubmenu: false,
    tabs: ["Bibliothek"], route: "/skills", component: SkillsPage },
  { id: "mcp", label: "MCP", icon: Server, hasSubmenu: false,
    tabs: ["Server"], route: "/mcp", component: McpPage, fullscreen: true },
  { id: "plugins", label: "Plugins", icon: Puzzle, hasSubmenu: false,
    tabs: ["Installiert"], route: "/plugins", component: PluginsPage, adminOnly: true },
  { id: "federation", label: "Föderation", icon: Globe, hasSubmenu: false,
    tabs: ["Instanzen"], route: "/federation", component: FederationPage },
  { id: "llm", label: "KI-Modelle", icon: Cpu, hasSubmenu: false,
    tabs: ["Provider & Modelle"], route: "/llm", component: LlmPage },
  { id: "credentials", label: "Zugangsdaten", icon: Key, hasSubmenu: false,
    tabs: ["Credentials"], route: "/credentials", component: CredentialsPage },

  { id: "extensions", label: "Erweiterungen", icon: Package, hasSubmenu: false,
    tabs: ["Installiert"], route: "/extensions", component: ExtensionsPage, adminOnly: true },
  { id: "modules", label: "Module", icon: Boxes, hasSubmenu: false,
    tabs: ["Verfügbar"], route: "/modules", component: ModulesPage, adminOnly: true },
  { id: "themes", label: "Themes", icon: Palette, hasSubmenu: false,
    tabs: ["Verfügbar"], route: "/themes", component: ThemesPage, adminOnly: true },
  { id: "connections", label: "Verbindungen", icon: Network, hasSubmenu: false,
    tabs: ["Tailscale", "AgentLink", "Samba"], route: "/system",
    tabComponents: { Tailscale: ConnTailscale, AgentLink: ConnAgentLink, Samba: ConnSamba } },
  { id: "system", label: "System", icon: SlidersHorizontal, hasSubmenu: false,
    tabs: ["Status", "Backup", "Bridge"], route: "/system", adminOnly: true,
    tabComponents: { Status: SysStatus, Backup: SysBackup, Bridge: SysBridge } },
  { id: "settings_values", label: "Globale Settings", icon: Database, hasSubmenu: false,
    tabs: ["Werte"], route: "/system/settings", component: SettingsPage, adminOnly: true },
  { id: "users", label: "Benutzer", icon: Users, hasSubmenu: false,
    tabs: ["Verwaltung"], route: "/users", component: UsersPage, adminOnly: true },
]
