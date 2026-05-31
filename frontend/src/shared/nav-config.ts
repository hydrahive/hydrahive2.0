import { Activity, BrainCircuit,
  BookOpen, Bot, Box, Cpu, Film, FolderKanban, Globe, HardDrive, Heart, Key, LayoutDashboard,
  MessageCircle, MessageSquare, MoonStar, Package, Pickaxe, Puzzle, Server, Settings, Sparkles, StickyNote, Users, Workflow,
} from "lucide-react"

export interface NavGroup {
  key: string
  labelKey: string
}

export interface NavItem {
  path: string
  icon: typeof Bot
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
  { path: "/health",      icon: Activity,        labelKey: "health",      group: "overview" },
  // Arbeiten
  { path: "/",            icon: Heart,           labelKey: "buddy",       group: "working" },
  { path: "/scratchpad",  icon: StickyNote,      labelKey: "scratchpad",  group: "working" },
  { path: "/werkstatt",   icon: MessageSquare,   labelKey: "werkstatt",   group: "working" },
  { path: "/agents",      icon: Bot,             labelKey: "agents",      group: "working" },
  { path: "/projects",    icon: FolderKanban,    labelKey: "projects",    group: "working" },
  { path: "/communication", icon: MessageCircle, labelKey: "communication", group: "working" },
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
  // Einstellungen
  { path: "/llm",         icon: Cpu,             labelKey: "llm",         group: "settings" },
  { path: "/credentials", icon: Key,             labelKey: "credentials", group: "settings" },
  { path: "/memory",      icon: BrainCircuit,    labelKey: "memory",      group: "settings" },
  { path: "/extensions",  icon: Package,         labelKey: "extensions",  group: "settings", roles: ["admin"] },
  { path: "/users",       icon: Users,           labelKey: "users",       group: "settings", roles: ["admin"] },
  { path: "/system",      icon: Settings,        labelKey: "system",      group: "settings" },
  { path: "/help",        icon: BookOpen,        labelKey: "help",        group: "settings" },
]

export const QUICK_LINK_PATHS = ["/dashboard", "/werkstatt", "/agents", "/projects"]

export function visibleItems(role: string | null): NavItem[] {
  return NAV_ITEMS.filter((i) =>
    !i.roles || (role !== null && i.roles.includes(role as "admin" | "user"))
  )
}
