import type { ReactNode } from "react"
import { CockpitButton } from "./CockpitButton"

interface Props {
  active: "projects" | "buddy" | "media" | "vault" | "admin"
  context?: string
  action?: { label: string; path: string }
  extraActions?: ReactNode
}

const nav = [
  { id: "projects", label: "Projekte", path: "/projects" },
  { id: "buddy", label: "Buddy", path: "/buddy" },
  { id: "media", label: "Media", path: "/media" },
  { id: "vault", label: "Vault", path: "/vault" },
  { id: "admin", label: "Admin", path: "/admin" },
  { id: "help", label: "Hilfe", path: "/help" },
] as const

export function CockpitTopbar({ active, context, action, extraActions }: Props) {
  return (
    <header className="flex h-[58px] shrink-0 items-center gap-[18px] border-b border-[#2a364b] bg-gradient-to-b from-[#131b2a] to-[#0e1420] px-[18px]">
      <button onClick={() => window.open("/projects", "_self")} className="font-black tracking-[-0.03em] text-[#e8eef8]">HydraHive</button>
      <nav className="flex gap-1.5 text-sm">
        {nav.map((item) => {
          const isActive = item.id === active
          return (
            <button
              key={item.id}
              onClick={() => window.open(item.path, "_self")}
              className={isActive
                ? "rounded-[4px] bg-[#1c2940] px-3 py-2 font-semibold text-[#69d7ff]"
                : "rounded-[4px] px-3 py-2 text-[#8d9ab0] hover:bg-white/[6%] hover:text-[#e8eef8]"}
            >
              {item.label}
            </button>
          )
        })}
      </nav>
      <div className="flex-1" />
      {context ? <div className="hidden text-xs text-[#8d9ab0] lg:block">{context}</div> : null}
      {extraActions}
      {action ? <CockpitButton onClick={() => window.open(action.path, "_self")}>{action.label}</CockpitButton> : null}
      <CockpitButton onClick={() => window.open("/settings", "_self")}>Profil</CockpitButton>
    </header>
  )
}
