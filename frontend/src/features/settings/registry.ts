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

// Agenten/Projekte: Auswahlfeld mit Suche + Formular (statt Liste am Rand).
const AgentSection = lazy(() => import("./detail/AgentSection").then((m) => ({ default: m.AgentSection })))
const ProjectSection = lazy(() => import("./detail/ProjectSection").then((m) => ({ default: m.ProjectSection })))

/**
 * Gruppen von „Meine Einstellungen“ (SSOT für die Reiterleiste oben).
 *
 * Jede Gruppe ist ein Reiter (URL /settings/:groupId). Nur persönliche Einstellungen;
 * Admin-Einstellungen leben im Admin-Cockpit (legacyRedirects.ts leitet alte Adressen um).
 * Tills Vorgabe: hier NUR Einstellungen; Auswertungen bleiben auf den Feature-Seiten.
 * Kompakt (docs/plans/meine-einstellungen-kompakt.md): keine Spalten links/rechts,
 * innere Reiter nur, wo eine Gruppe mehrere Teile hat (`tabs` mit > 1 Eintrag).
 */
export interface SettingsGroup {
  id: string
  label: string
  icon: LucideIcon
  /** Innere Reiter (Name → Komponente). Leer = die Gruppe hat genau einen Inhalt (`component`). */
  tabs: string[]
  tabComponents?: Record<string, LazyExoticComponent<ComponentType>>
  component?: LazyExoticComponent<ComponentType>
  /** Inhalt bringt eigenes Layout mit voller Höhe mit (Butler-Editor, Agenten/Projekte): kein Innenabstand. */
  fullHeight?: boolean
  adminOnly?: boolean
}

export const SETTINGS_GROUPS: SettingsGroup[] = [
  { id: "agents", label: "Agenten", icon: Bot, tabs: [], component: AgentSection, fullHeight: true },
  { id: "projects", label: "Projekte", icon: FolderKanban, tabs: [], component: ProjectSection, fullHeight: true },
  { id: "communication", label: "Kommunikation", icon: MessageCircle, tabs: ["Discord", "WhatsApp", "Mail"],
    tabComponents: { Discord: CommDiscord, WhatsApp: CommWhatsApp, Mail: CommMail } },
  { id: "credentials", label: "Zugangsdaten", icon: Key, tabs: [], component: CredentialsPage },
  { id: "skills", label: "Skills", icon: Sparkles, tabs: [], component: SkillsPage },
  { id: "butler", label: "Butler", icon: Workflow, tabs: [], component: ButlerPage, fullHeight: true },
]
