import { lazy, type LazyExoticComponent, type ComponentType } from "react"
import { Bot, FolderKanban, Key, MessageCircle, Sparkles, Workflow, type LucideIcon } from "lucide-react"

// Lazy-geladene Feature-Pages, die direkt eingebettet werden (nur geladen, wenn die Gruppe offen ist).
const CredentialsPage = lazy(() => import("@/features/credentials/CredentialsPage").then((m) => ({ default: m.CredentialsPage })))
const SkillsPage = lazy(() => import("@/features/skills/SkillsPage").then((m) => ({ default: m.SkillsPage })))
const ButlerPage = lazy(() => import("@/features/butler/ButlerPage").then((m) => ({ default: m.ButlerPage })))

// Per-Tab-Inhalte der Gruppe Kommunikation.
const CommDiscord = lazy(() => import("./tabs/CommunicationTabs").then((m) => ({ default: m.CommDiscord })))
const CommWhatsApp = lazy(() => import("./tabs/CommunicationTabs").then((m) => ({ default: m.CommWhatsApp })))
const CommMail = lazy(() => import("./tabs/CommunicationTabs").then((m) => ({ default: m.CommMail })))

// Detail-Komponenten (Submenü-Schema): Einstellungen des gewählten Agenten/Projekts.
const AgentSettings = lazy(() => import("./detail/AgentSettings").then((m) => ({ default: m.AgentSettings })))
const AgentSubMenu = lazy(() => import("./detail/AgentSubMenu").then((m) => ({ default: m.AgentSubMenu })))
const ProjectSettings = lazy(() => import("./detail/ProjectSettings").then((m) => ({ default: m.ProjectSettings })))
const ProjectSubMenu = lazy(() => import("./detail/ProjectSubMenu").then((m) => ({ default: m.ProjectSubMenu })))

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
  // „Meine Einstellungen“: nur, was jeder Nutzer für sich einstellt. Admin-Einstellungen
  // (Module, KI-Modelle, System, Benutzer …) leben im Admin-Cockpit; alte Adressen leiten
  // per legacyRedirects.ts dorthin um (docs/plans/meine-einstellungen.md).
  { id: "agents", label: "Agenten", icon: Bot, hasSubmenu: true,
    submenuLabel: "Agenten", tabs: ["Einstellungen"], route: "/agents",
    detailComponent: AgentSettings, submenuComponent: AgentSubMenu },
  { id: "projects", label: "Projekte", icon: FolderKanban, hasSubmenu: true,
    submenuLabel: "Projekte", tabs: ["Einstellungen"], route: "/projects",
    detailComponent: ProjectSettings, submenuComponent: ProjectSubMenu },
  { id: "communication", label: "Kommunikation", icon: MessageCircle, hasSubmenu: false,
    tabs: ["Discord", "WhatsApp", "Mail"], route: "/communication",
    tabComponents: { Discord: CommDiscord, WhatsApp: CommWhatsApp, Mail: CommMail } },
  { id: "credentials", label: "Zugangsdaten", icon: Key, hasSubmenu: false,
    tabs: ["Credentials"], route: "/credentials", component: CredentialsPage },
  { id: "skills", label: "Skills", icon: Sparkles, hasSubmenu: false,
    tabs: ["Bibliothek"], route: "/skills", component: SkillsPage },
  { id: "butler", label: "Butler", icon: Workflow, hasSubmenu: false,
    tabs: ["Flows"], route: "/butler", component: ButlerPage, fullscreen: true },
]
