import { BrainCircuit,
  BookOpen, Bot, Box, Film, FolderKanban, Globe, HardDrive, Heart, LayoutDashboard,
  MessageCircle, MessageSquare, MessagesSquare, MoonStar, Pickaxe, Puzzle, Server, Shield, Sparkles, Workflow,
} from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { moduleNav } from "@/modules/index.generated"
import { moduleIcon } from "@/shared/module-icon"

export interface NavGroup {
  key: string
  labelKey: string
}

interface ModuleNavEntry {
  path: string
  icon: string
  labelKey: string
  group?: string
  roles?: ("admin" | "user")[]
}

export interface NavItem {
  path: string
  icon: LucideIcon
  labelKey: string
  group: string
  roles?: ("admin" | "user")[]
}

export const NAV_GROUPS: NavGroup[] = [
  { key: "overview",       labelKey: "groupOverview" },
  { key: "working",        labelKey: "groupWorking" },
  { key: "automation",     labelKey: "groupAutomation" },
  { key: "infrastructure", labelKey: "groupInfrastructure" },
  { key: "settings",       labelKey: "groupSettings" },
]

export const NAV_ITEMS: NavItem[] = [
  // Überblick
  { path: "/dashboard",   icon: LayoutDashboard, labelKey: "dashboard",   group: "overview" },
  // Cockpits
  { path: "/projects",    icon: FolderKanban,    labelKey: "projects",    group: "working" },
  { path: "/buddy",       icon: Heart,           labelKey: "buddy",       group: "working" },
  { path: "/media",       icon: Film,            labelKey: "media",       group: "working" },
  { path: "/vault",       icon: Shield,          labelKey: "vault",       group: "working" },
  { path: "/admin",       icon: Server,          labelKey: "admin",       group: "working", roles: ["admin"] },
  // Alte Arbeitsbereiche bleiben erreichbar, verschwinden aber aus den Quicklinks.
  { path: "/werkstatt",   icon: MessageSquare,   labelKey: "werkstatt",   group: "working" },
  { path: "/settings/agents",   icon: Bot,          labelKey: "agents",   group: "working" },
  { path: "/settings/projects", icon: FolderKanban, labelKey: "projectSettings", group: "working" },
  { path: "/communication", icon: MessageCircle, labelKey: "communication", group: "working" },
  { path: "/teamchat",    icon: MessagesSquare,  labelKey: "teamchat",    group: "working" },
  // Automatisierung
  { path: "/butler",      icon: Workflow,        labelKey: "butler",      group: "automation" },
  { path: "/zahnfee",     icon: MoonStar,        labelKey: "zahnfee",     group: "automation", roles: ["admin"] },
  { path: "/skills",      icon: Sparkles,        labelKey: "skills",      group: "automation" },
  { path: "/mcp",         icon: Server,          labelKey: "mcp",         group: "automation" },
  { path: "/plugins",     icon: Puzzle,          labelKey: "plugins",     group: "automation", roles: ["admin"] },
  // Infrastruktur
  { path: "/vms",         icon: HardDrive,       labelKey: "vms",         group: "infrastructure" },
  { path: "/containers",  icon: Box,             labelKey: "containers",  group: "infrastructure" },
  { path: "/federation",  icon: Globe,           labelKey: "federation",  group: "infrastructure" },
  { path: "/streaming",   icon: Film,            labelKey: "streaming",   group: "infrastructure" },
  { path: "/datamining",  icon: Pickaxe,         labelKey: "datamining",  group: "infrastructure" },
  // Gedächtnis = Auswertung (kein Setting) → bei den Infrastruktur-/Analyse-Tools.
  { path: "/memory",      icon: BrainCircuit,    labelKey: "memory",      group: "infrastructure" },

  // Einstellungen: LLM/Credentials/Extensions/Module/Benutzer/System sind jetzt
  // alle gebündelt im zentralen Settings-Hub (Zahnrad → /settings) erreichbar,
  // daher hier KEINE Einzeleinträge mehr. Nur Hilfe bleibt.
  { path: "/help",        icon: BookOpen,        labelKey: "help",        group: "settings" },
]

export const QUICK_LINK_PATHS = ["/projects", "/buddy", "/media", "/vault", "/admin"]

const MODULE_NAV_ITEMS: NavItem[] = (moduleNav as ModuleNavEntry[]).map((n) => ({
  path: n.path,
  icon: moduleIcon(n.icon),
  labelKey: n.labelKey,
  group: n.group ?? "working",
  roles: n.roles,
}))

export function visibleItems(role: string | null): NavItem[] {
  const all = [...NAV_ITEMS, ...MODULE_NAV_ITEMS]
  return all.filter((i) =>
    !i.roles || i.roles.length === 0 || (role !== null && i.roles.includes(role as "admin" | "user"))
  )
}
