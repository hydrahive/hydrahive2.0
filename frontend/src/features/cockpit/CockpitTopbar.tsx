import { useEffect, useRef, useState, type ReactNode } from "react"
import { Menu, MoreHorizontal, X } from "lucide-react"
import { HelpButton } from "@/i18n/HelpButton"
import type { HelpTopic } from "@/i18n/help/loader"
import { CockpitButton } from "./CockpitButton"
import { CockpitAppsMenu } from "./CockpitAppsMenu"
import { CockpitUserMenu } from "./CockpitUserMenu"

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

const go = (path: string) => window.open(path, "_self")
const HELP_TOPICS: Record<Props["active"], HelpTopic> = {
  projects: "projects",
  buddy: "buddy",
  media: "atelier",
  vault: "patientenakte",
  admin: "system",
}

export function CockpitTopbar({ active, context, action, extraActions }: Props) {
  const [menuOpen, setMenuOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLElement>(null)

  function closeMenu(restoreFocus = true) {
    setMenuOpen(false)
    if (restoreFocus) window.setTimeout(() => triggerRef.current?.focus(), 0)
  }

  useEffect(() => {
    if (!menuOpen) return
    menuRef.current?.querySelector<HTMLButtonElement>("button")?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeMenu()
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [menuOpen])

  const activeLabel = nav.find((item) => item.id === active)?.label ?? "Cockpit"

  return (
    <header className="relative flex h-[58px] shrink-0 items-center gap-3 border-b border-[#2a364b] bg-gradient-to-b from-[#131b2a] to-[#0e1420] px-3 sm:px-[18px]">
      <button onClick={() => go("/projects")} className="shrink-0 font-black tracking-[-0.03em] text-[#e8eef8]">HydraHive</button>
      <span className="truncate text-xs font-semibold text-[#69d7ff] sm:hidden">{activeLabel}</span>
      <nav className="hidden gap-1 text-sm sm:flex" aria-label="Cockpit-Bereiche">
        {nav.map((item) => <NavButton key={item.id} item={item} active={item.id === active} />)}
      </nav>
      <div className="min-w-0 flex-1" />
      {context ? <div className="hidden max-w-52 truncate text-xs text-[#8d9ab0] 2xl:block" title={context}>{context}</div> : null}
      <div className="hidden items-center gap-2 2xl:flex">
        {extraActions}
        {action ? <CockpitButton onClick={() => go(action.path)}>{action.label}</CockpitButton> : null}
        <CockpitAppsMenu />
        <HelpButton topic={HELP_TOPICS[active]} />
        <CockpitUserMenu />
      </div>
      <button
        ref={triggerRef}
        onClick={() => setMenuOpen((open) => !open)}
        aria-expanded={menuOpen}
        aria-controls="cockpit-responsive-menu"
        aria-label={menuOpen ? "Cockpit-Menü schließen" : "Cockpit-Menü öffnen"}
        className="rounded-[4px] border border-[#2a364b] bg-[#172133] p-2 text-[#e8eef8] hover:border-[#46617f] 2xl:hidden"
      >
        <span className="hidden items-center gap-2 sm:flex"><MoreHorizontal size={16} /><span className="text-xs font-bold">Aktionen</span></span>
        <span className="sm:hidden">{menuOpen ? <X size={18} /> : <Menu size={18} />}</span>
      </button>

      {menuOpen && <>
        <button className="fixed inset-0 z-[109] cursor-default bg-black/55 2xl:hidden" aria-label="Menü schließen" onClick={() => closeMenu()} />
        <section ref={menuRef} id="cockpit-responsive-menu" role="dialog" aria-modal="true" aria-label="Cockpit-Menü" className="fixed inset-y-0 right-0 z-[110] flex w-[min(360px,88vw)] flex-col overflow-y-auto border-l border-[#2a364b] bg-[#101724] p-4 shadow-2xl sm:absolute sm:inset-y-auto sm:right-3 sm:top-[52px] sm:max-h-[calc(100dvh-64px)] sm:w-80 sm:rounded-[6px] sm:border">
          <div className="mb-3 flex items-center justify-between"><div><p className="text-xs uppercase tracking-wider text-[#718097]">Cockpit</p><p className="font-semibold text-[#e8eef8]">{activeLabel}</p></div><button onClick={() => closeMenu()} className="rounded p-2 text-[#8d9ab0] hover:bg-white/5 hover:text-white" aria-label="Menü schließen"><X size={18} /></button></div>
          {context && <p className="mb-3 rounded-[4px] border border-[#2a364b] bg-[#151c2b] px-3 py-2 text-xs text-[#8d9ab0]">{context}</p>}
          <nav className="mb-4 grid gap-1 sm:hidden" aria-label="Cockpit-Bereiche mobil">
            {nav.map((item) => <NavButton key={item.id} item={item} active={item.id === active} onNavigate={() => closeMenu(false)} />)}
          </nav>
          <div className="grid gap-2 border-t border-[#2a364b] pt-4 sm:border-0 sm:pt-0">
            <div className="contents [&>button]:w-full">{extraActions}</div>
            {action ? <CockpitButton onClick={() => go(action.path)}>{action.label}</CockpitButton> : null}
            <CockpitAppsMenu compact />
            <HelpButton topic={HELP_TOPICS[active]} className="w-full justify-center" />
            <CockpitUserMenu compact />
          </div>
        </section>
      </>}
    </header>
  )
}

function NavButton({ item, active, onNavigate }: {
  item: (typeof nav)[number]
  active: boolean
  onNavigate?: () => void
}) {
  return <button onClick={() => { onNavigate?.(); go(item.path) }} className={active ? "rounded-[4px] bg-[#1c2940] px-3 py-2 text-left font-semibold text-[#69d7ff]" : "rounded-[4px] px-3 py-2 text-left text-[#8d9ab0] hover:bg-white/[6%] hover:text-[#e8eef8]"}>{item.label}</button>
}
