// Bereichs-Leiste oben (docs/specs/startdesktop.md): ⌂ Start · Bereich ▾ · Apps des Bereichs · Kasten ⊞.
// Ersetzt die frühere Cockpit-Leiste; CockpitTopbar reicht seine Props hierher durch.
import { useEffect, type ReactNode } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { Home } from "lucide-react"
import { HelpButton } from "@/i18n/HelpButton"
import type { HelpTopic } from "@/i18n/help/loader"
import { VaultBadge } from "@/features/vault/VaultBadge"
import { CockpitUserMenu } from "@/features/cockpit/CockpitUserMenu"
import { AreaAppsMenu } from "./AreaAppsMenu"
import { AreaSwitcher } from "./AreaSwitcher"
import { areaForPath, entryPath } from "./areaLogic"
import { useAreaPrefs } from "./useAreaPrefs"
import { useAreas } from "./useAreas"

export interface AreaTopbarProps {
  /** Seitenknopf, z. B. „Buddy-Settings“. */
  action?: { label: string; path: string }
  extraActions?: ReactNode
  help?: HelpTopic
}

export function AreaTopbar({ action, extraActions, help = "onboarding" }: AreaTopbarProps) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { areas, label } = useAreas()
  const prefs = useAreaPrefs()
  const hit = areaForPath(areas, pathname)
  const active = hit?.area ?? areas.find((a) => a.area.id === prefs.active) ?? null

  // Bereich folgt der geöffneten App; der genaue Pfad wird als „zuletzt benutzt“ gemerkt.
  useEffect(() => {
    if (hit) prefs.remember(hit.area.area.id, pathname)
  }, [hit?.area.area.id, pathname]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <header className="relative flex h-[58px] shrink-0 items-center gap-2 border-b border-[#2a364b] bg-gradient-to-b from-[#131b2a] to-[#0e1420] px-3 sm:gap-3 sm:px-[18px]">
      <button type="button" onClick={() => navigate("/start")} title="Start – alle Bereiche" aria-label="Start"
        className="flex shrink-0 items-center gap-1.5 font-black tracking-[-0.03em] text-[#e8eef8]">
        <Home size={16} className="text-[#69d7ff]" /><span className="hidden md:inline">HydraHive</span>
      </button>

      <AreaSwitcher areas={areas} active={active}
        onPick={(a) => { prefs.setActive(a.area.id); navigate(entryPath(a, prefs.last)) }} />

      <nav className="hidden min-w-0 flex-1 items-center gap-0.5 overflow-x-auto text-sm sm:flex" aria-label="Apps im Bereich">
        {active?.items.map((i) => {
          const on = hit?.item.path === i.path
          return (
            <button key={i.path} type="button" onClick={() => navigate(i.path)} aria-current={on ? "page" : undefined}
              className={`shrink-0 rounded-[4px] px-2.5 py-2 ${on ? `bg-[#1c2940] font-semibold ${active.area.text}` : "text-[#8d9ab0] hover:bg-white/[6%] hover:text-[#e8eef8]"}`}>
              {label(i)}
            </button>
          )
        })}
      </nav>
      <div className="min-w-0 flex-1 sm:hidden" />

      <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
        {extraActions && <div className="hidden items-center gap-2 lg:flex">{extraActions}</div>}
        {action && (
          <button type="button" onClick={() => navigate(action.path)}
            className="hidden rounded-[4px] border border-[#2a364b] bg-[#172133] px-3 py-1.5 text-xs font-bold text-[#e8eef8] hover:border-[#46617f] md:block">
            {action.label}
          </button>
        )}
        <div className="hidden xl:block"><VaultBadge /></div>
        <AreaAppsMenu areas={areas} activeId={active?.area.id ?? null} label={label} onOpen={(p) => navigate(p)} action={action} extraActions={extraActions} />
        <div className="hidden lg:block"><HelpButton topic={help} /></div>
        <CockpitUserMenu />
      </div>
    </header>
  )
}
