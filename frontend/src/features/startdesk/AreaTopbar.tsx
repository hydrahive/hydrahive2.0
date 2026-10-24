// VORSCHAU Startdesktop: Bereichs-Leiste oben. ⌂ Start · Bereichs-Umschalter · Apps des Bereichs · Kasten.
import { useEffect, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { ChevronDown, Home } from "lucide-react"
import { HelpButton } from "@/i18n/HelpButton"
import { VaultBadge } from "@/features/vault/VaultBadge"
import { CockpitUserMenu } from "@/features/cockpit/CockpitUserMenu"
import { AreaAppsMenu } from "./AreaAppsMenu"
import { areaForPath, rememberLast, storeArea, storedArea } from "./areaState"
import { useAreas } from "./useAreas"

export function AreaTopbar() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { groups, label } = useAreas()
  const [switcher, setSwitcher] = useState(false)
  const hit = areaForPath(groups, pathname)
  const active = hit?.area ?? groups.find((g) => g.group.id === storedArea()) ?? null

  // Bereich folgt der geöffneten App und merkt sich die zuletzt benutzte App.
  useEffect(() => {
    if (!hit) return
    storeArea(hit.area.group.id)
    rememberLast(hit.area.group.id, hit.item.path)
  }, [hit?.area.group.id, hit?.item.path]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!switcher) return
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setSwitcher(false) }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [switcher])

  const tone = active ? active.group.tone.split(" ").filter((c) => c.startsWith("text-")).join(" ") : "text-[#69d7ff]"
  const AreaIcon = active?.group.icon

  return (
    <header className="relative flex h-[58px] shrink-0 items-center gap-2 border-b border-[#2a364b] bg-gradient-to-b from-[#131b2a] to-[#0e1420] px-3 sm:gap-3 sm:px-[18px]">
      <button type="button" onClick={() => navigate("/start-vorschau")} title="Start – alle Bereiche" aria-label="Start"
        className="flex shrink-0 items-center gap-1.5 font-black tracking-[-0.03em] text-[#e8eef8]">
        <Home size={16} className="text-[#69d7ff]" /><span className="hidden md:inline">HydraHive</span>
      </button>

      <div className="relative min-w-0 shrink-0">
        <button type="button" onClick={() => setSwitcher((o) => !o)} aria-expanded={switcher} aria-haspopup="menu"
          className={`flex max-w-[52vw] items-center gap-1.5 rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2.5 py-1.5 text-sm font-bold hover:border-[#46617f] sm:max-w-none ${tone}`}>
          {AreaIcon && <AreaIcon size={15} className="shrink-0" />}
          <span className="truncate">{active ? active.group.title : "Bereich wählen"}</span>
          <ChevronDown size={14} className="shrink-0 text-[#8d9ab0]" />
        </button>
        {switcher && <>
          <button type="button" className="fixed inset-0 z-[119] cursor-default" aria-label="Bereiche schließen" onClick={() => setSwitcher(false)} />
          <div role="menu" className="absolute left-0 top-10 z-[120] w-[min(300px,calc(100vw-24px))] rounded-[6px] border border-[#2a364b] bg-[#101724] p-1 shadow-2xl">
            {groups.map((g) => {
              const Icon = g.group.icon
              const t = g.group.tone.split(" ").filter((c) => c.startsWith("text-")).join(" ")
              const on = g.group.id === active?.group.id
              return <button key={g.group.id} type="button" role="menuitem"
                onClick={() => { setSwitcher(false); storeArea(g.group.id); navigate(g.items[0].path) }}
                className={`flex w-full items-center gap-2.5 rounded-[4px] px-2.5 py-2 text-left hover:bg-[#172133] ${on ? "bg-[#172133]" : ""}`}>
                <Icon size={16} className={`shrink-0 ${t}`} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-bold text-[#e8eef8]">{g.group.title}</span>
                  <span className="block truncate text-[11px] text-[#718097]">{g.group.blurb}</span>
                </span>
                <span className="text-[11px] text-[#718097]">{g.items.length}</span>
              </button>
            })}
          </div>
        </>}
      </div>

      <nav className="hidden min-w-0 flex-1 items-center gap-0.5 overflow-x-auto text-sm sm:flex" aria-label="Apps im Bereich">
        {active?.items.map((i) => {
          const on = hit?.item.path === i.path
          return <button key={i.path} type="button" onClick={() => navigate(i.path)}
            className={`shrink-0 rounded-[4px] px-2.5 py-2 ${on ? `bg-[#1c2940] font-semibold ${tone}` : "text-[#8d9ab0] hover:bg-white/[6%] hover:text-[#e8eef8]"}`}>
            {label(i)}
          </button>
        })}
      </nav>
      <div className="min-w-0 flex-1 sm:hidden" />

      <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
        <div className="hidden xl:block"><VaultBadge /></div>
        <AreaAppsMenu groups={groups} activeId={active?.group.id ?? null} label={label} onOpen={(p) => navigate(p)} />
        <div className="hidden lg:block"><HelpButton topic="onboarding" /></div>
        <CockpitUserMenu />
      </div>
    </header>
  )
}
