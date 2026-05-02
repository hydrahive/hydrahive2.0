import {
  BookOpen, Bot, Box, Cpu, FolderKanban, HardDrive, Heart, Key, LayoutDashboard,
  MessageCircle, MessageSquare, Puzzle, Server, Settings, Sparkles, Users, Workflow,
} from "lucide-react"

export interface NavItem {
  path: string
  icon: typeof Bot
  labelKey: string
  roles?: ("admin" | "user")[]
}

// Alle Apps — werden im Bento-Menü angezeigt.
// Quick-Links in der Top-Bar wählen wir aus dieser Liste.
export const NAV_ITEMS: NavItem[] = [
  { path: "/", icon: Heart, labelKey: "buddy" },
  { path: "/dashboard", icon: LayoutDashboard, labelKey: "dashboard" },
  { path: "/devchat", icon: MessageSquare, labelKey: "devchat" },
  { path: "/agents", icon: Bot, labelKey: "agents" },
  { path: "/projects", icon: FolderKanban, labelKey: "projects" },
  { path: "/communication", icon: MessageCircle, labelKey: "communication" },
  { path: "/butler", icon: Workflow, labelKey: "butler" },
  { path: "/vms", icon: HardDrive, labelKey: "vms" },
  { path: "/containers", icon: Box, labelKey: "containers" },
  { path: "/llm", icon: Cpu, labelKey: "llm" },
  { path: "/mcp", icon: Server, labelKey: "mcp" },
  { path: "/skills", icon: Sparkles, labelKey: "skills" },
  { path: "/credentials", icon: Key, labelKey: "credentials" },
  { path: "/users", icon: Users, labelKey: "users", roles: ["admin"] },
  { path: "/plugins", icon: Puzzle, labelKey: "plugins", roles: ["admin"] },
  { path: "/system", icon: Settings, labelKey: "system" },
  { path: "/help", icon: BookOpen, labelKey: "help" },
]

// Quick-Links direkt in der Top-Bar — die wichtigsten Apps.
export const QUICK_LINK_PATHS = ["/dashboard", "/devchat", "/agents", "/projects"]

export function visibleItems(role: string | null): NavItem[] {
  return NAV_ITEMS.filter((i) =>
    !i.roles || (role !== null && i.roles.includes(role as "admin" | "user"))
  )
}
