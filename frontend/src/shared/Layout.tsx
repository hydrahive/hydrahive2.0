import { Link, Outlet, useLocation } from "react-router-dom"
import { Bot, Cpu, FolderKanban, LayoutDashboard, LogOut, MessageSquare, Settings } from "lucide-react"
import { cn } from "./cn"
import { useAuthStore } from "@/features/auth/useAuthStore"

const NAV_GROUPS = [
  {
    label: "Hauptmenü",
    items: [
      { path: "/", icon: LayoutDashboard, label: "Dashboard" },
      { path: "/chat", icon: MessageSquare, label: "Chat" },
      { path: "/agents", icon: Bot, label: "Agenten" },
      { path: "/projects", icon: FolderKanban, label: "Projekte" },
    ],
  },
  {
    label: "Konfiguration",
    items: [
      { path: "/llm", icon: Cpu, label: "LLM" },
      { path: "/system", icon: Settings, label: "System" },
    ],
  },
]

const ALL_NAV = NAV_GROUPS.flatMap((g) => g.items)

function useActive(path: string) {
  const { pathname } = useLocation()
  return path === "/" ? pathname === "/" : pathname.startsWith(path)
}

function SideNavItem({ path, icon: Icon, label }: { path: string; icon: typeof Bot; label: string }) {
  const active = useActive(path)
  return (
    <Link
      to={path}
      className={cn(
        "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150",
        active
          ? "bg-gradient-to-r from-indigo-600/20 to-violet-600/10 text-white border-l-2 border-violet-500 pl-[10px] shadow-[0_0_14px_rgba(139,92,246,0.22)]"
          : "text-zinc-400 hover:text-zinc-200 hover:bg-white/5 border-l-2 border-transparent pl-[10px]"
      )}
    >
      <Icon size={16} className={active ? "text-violet-400" : ""} />
      <span>{label}</span>
    </Link>
  )
}

function BottomNavItem({ path, icon: Icon, label }: { path: string; icon: typeof Bot; label: string }) {
  const active = useActive(path)
  return (
    <Link
      to={path}
      className={cn(
        "flex-1 flex flex-col items-center gap-1 py-2.5 text-xs transition-colors",
        active ? "text-violet-400" : "text-zinc-500 hover:text-zinc-300"
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
    <div className="flex h-screen overflow-hidden bg-[#020617]">
      {/* Ambient background glows */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-32 left-1/4 w-[500px] h-[500px] bg-violet-600/[13%] rounded-full blur-3xl" />
        <div className="absolute top-1/2 -right-20 w-96 h-96 bg-indigo-600/[10%] rounded-full blur-3xl" />
        <div className="absolute -bottom-20 left-1/3 w-80 h-80 bg-purple-700/[10%] rounded-full blur-3xl" />
        <div className="absolute top-1/3 left-0 w-64 h-64 bg-violet-800/[7%] rounded-full blur-2xl" />
      </div>

      {/* Sidebar — Desktop */}
      <aside className="hidden md:flex flex-col w-60 shrink-0 border-r border-white/[6%] bg-zinc-950/80 relative z-10">
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 h-14 border-b border-white/[6%]">
          <div className="relative">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 via-violet-600 to-purple-700 flex items-center justify-center text-sm shadow-lg shadow-violet-900/50">
              🐝
            </div>
            <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-indigo-500 via-violet-600 to-purple-700 blur-md opacity-50 -z-10 scale-110" />
          </div>
          <span className="font-bold bg-gradient-to-r from-indigo-300 via-violet-300 to-purple-300 bg-clip-text text-transparent tracking-tight">
            HydraHive
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-4">
          {NAV_GROUPS.map((group) => (
            <div key={group.label}>
              <p className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
                {group.label}
              </p>
              <div className="space-y-0.5">
                {group.items.map((item) => (
                  <SideNavItem key={item.path} {...item} />
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* User Footer */}
        <div className="mx-2 mb-3 rounded-xl bg-white/[3%] border border-white/[6%] p-3">
          <div className="flex items-center gap-2.5">
            <div className="relative shrink-0">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-violet-700 flex items-center justify-center text-white text-xs font-bold shadow-md shadow-violet-900/30">
                {username?.[0]?.toUpperCase() ?? "?"}
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-zinc-950 shadow-[0_0_7px_rgba(52,211,153,0.65)]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-zinc-200 truncate">{username}</p>
              <p className="text-xs text-zinc-500">{role}</p>
            </div>
            <button
              onClick={logout}
              className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-white/10 transition-colors"
              title="Abmelden"
            >
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </aside>

      {/* Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative z-10">
        <main className="flex-1 overflow-y-auto p-4 md:p-6 pb-20 md:pb-6">
          <Outlet />
        </main>
      </div>

      {/* Bottom Nav — Mobile */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-20 bg-zinc-950/95 backdrop-blur border-t border-white/[6%] flex">
        {ALL_NAV.slice(0, 5).map((item) => (
          <BottomNavItem key={item.path} {...item} />
        ))}
      </nav>
    </div>
  )
}
