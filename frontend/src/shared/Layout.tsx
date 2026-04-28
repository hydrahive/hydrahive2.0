import { Link, Outlet, useLocation } from "react-router-dom"
import { Bot, FolderKanban, LayoutDashboard, LogOut, MessageSquare, Settings, Cpu } from "lucide-react"
import { cn } from "./cn"
import { useAuthStore } from "@/features/auth/useAuthStore"

const NAV = [
  { path: "/", icon: LayoutDashboard, label: "Dashboard" },
  { path: "/chat", icon: MessageSquare, label: "Chat" },
  { path: "/agents", icon: Bot, label: "Agenten" },
  { path: "/projects", icon: FolderKanban, label: "Projekte" },
  { path: "/llm", icon: Cpu, label: "LLM" },
  { path: "/system", icon: Settings, label: "System" },
]

function useActive(path: string) {
  const { pathname } = useLocation()
  return path === "/" ? pathname === "/" : pathname.startsWith(path)
}

function SideNavItem({ path, icon: Icon, label }: (typeof NAV)[0]) {
  const active = useActive(path)
  return (
    <Link
      to={path}
      className={cn(
        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
        active
          ? "bg-primary/15 text-primary"
          : "text-muted-foreground hover:text-foreground hover:bg-muted"
      )}
    >
      <Icon size={18} />
      <span>{label}</span>
    </Link>
  )
}

function BottomNavItem({ path, icon: Icon, label }: (typeof NAV)[0]) {
  const active = useActive(path)
  return (
    <Link
      to={path}
      className={cn(
        "flex-1 flex flex-col items-center gap-1 py-2.5 text-xs transition-colors",
        active ? "text-primary" : "text-muted-foreground"
      )}
    >
      <Icon size={20} />
      <span>{label}</span>
    </Link>
  )
}

export function Layout() {
  const { username, role, logout } = useAuthStore()

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar — Desktop */}
      <aside className="hidden md:flex flex-col w-60 shrink-0 border-r border-border bg-card">
        <div className="flex items-center gap-3 px-4 py-4 border-b border-border">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-600 to-violet-800 flex items-center justify-center text-sm">
            🐝
          </div>
          <span className="font-semibold text-foreground">HydraHive</span>
        </div>

        <nav className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {NAV.map((item) => <SideNavItem key={item.path} {...item} />)}
        </nav>

        <div className="p-3 border-t border-border">
          <div className="flex items-center gap-2 px-2 py-1.5">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-purple-500 to-violet-700 flex items-center justify-center text-white text-xs font-bold shrink-0">
              {username?.[0]?.toUpperCase() ?? "?"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">{username}</p>
              <p className="text-xs text-muted-foreground">{role}</p>
            </div>
            <button
              onClick={logout}
              className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              title="Abmelden"
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </aside>

      {/* Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <main className="flex-1 overflow-y-auto p-4 md:p-6 pb-20 md:pb-6">
          <Outlet />
        </main>
      </div>

      {/* Bottom Nav — Mobile */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-card border-t border-border flex">
        {NAV.slice(0, 5).map((item) => <BottomNavItem key={item.path} {...item} />)}
      </nav>
    </div>
  )
}
