// Startseite (docs/specs/startdesktop.md): Begrüßung, App-Suche, Buddy-Knopf, Bereichs-Kacheln.
// Klick auf einen Bereich öffnet direkt dessen zuletzt benutzte (sonst erste) App.
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Search } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import type { NavItem } from "@/shared/nav-config"
import { BuddyButton } from "./BuddyButton"
import { entryPath, type FilledArea } from "./areaLogic"
import { useAreaPrefs } from "./useAreaPrefs"
import { useAreas } from "./useAreas"

function greeting(now: Date): string {
  const h = now.getHours()
  return h < 11 ? "Guten Morgen" : h < 18 ? "Hallo" : "Guten Abend"
}

export function StartDeskPage() {
  const navigate = useNavigate()
  const username = useAuthStore((s) => s.username)
  const { areas, label } = useAreas()
  const prefs = useAreaPrefs()
  const [query, setQuery] = useState("")
  const needle = query.trim().toLowerCase()
  const hits = needle ? areas.flatMap((a) => a.items.map((i) => ({ i, a }))).filter(({ i }) => label(i).toLowerCase().includes(needle)) : []
  const openArea = (a: FilledArea) => { prefs.setActive(a.area.id); navigate(entryPath(a, prefs.last)) }

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-s-grund">
      <CockpitTopbar active="start" />
      <main className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
        <div className="mx-auto max-w-6xl">
          <div className="flex items-end gap-3 sm:gap-5">
            <img src="/startdesk/koepfe/hydra-voll.webp" alt="" aria-hidden="true" draggable={false}
              className="h-20 w-auto shrink-0 select-none drop-shadow-[0_6px_18px_rgba(0,0,0,0.45)] sm:h-28" />
            <div className="min-w-0 pb-1">
              <h1 className="text-xl font-black text-[#e8eef8] sm:text-3xl">{greeting(new Date())}{username ? `, ${username}` : ""}</h1>
              <p className="mt-1 text-sm text-[#9aa7bc]">Wohin möchtest du?</p>
            </div>
          </div>
          <label className="mt-4 flex max-w-xl items-center gap-2 rounded-[6px] border border-s-rand bg-s-tief px-3 py-2.5 focus-within:border-s-rand-hover">
            <Search size={16} className="shrink-0 text-[#9aa7bc]" />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="App suchen …" aria-label="App suchen"
              onKeyDown={(e) => { if (e.key === "Enter" && hits[0]) navigate(hits[0].i.path) }}
              className="min-w-0 flex-1 bg-transparent text-sm text-[#e8eef8] placeholder:text-[#5f6d84] focus:outline-none" />
          </label>
          {needle ? (
            <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {hits.length === 0 && <p className="col-span-full text-sm text-[#9aa7bc]">Nichts gefunden.</p>}
              {hits.map(({ i, a }) => <AppTile key={i.path} item={i} label={label(i)} area={a} onOpen={() => navigate(i.path)} />)}
            </div>
          ) : (
            <>
              <BuddyButton onOpen={() => navigate("/buddy")} />
              <div className="mt-4 grid grid-cols-2 gap-2.5 sm:gap-3 lg:grid-cols-4">
                {areas.map((a) => <AreaTile key={a.area.id} fa={a} label={label} onOpen={() => openArea(a)} />)}
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  )
}

function AreaTile({ fa, label, onOpen }: { fa: FilledArea; label: (i: NavItem) => string; onOpen: () => void }) {
  const { area, items } = fa
  const Icon = area.icon
  return (
    <button type="button" onClick={onOpen} data-area-tile={area.id}
      className={`group flex min-h-[118px] overflow-hidden rounded-[8px] border bg-gradient-to-br to-s-box p-3 text-left transition hover:-translate-y-0.5 hover:shadow-xl hover:shadow-black/40 sm:min-h-[150px] sm:p-4 ${area.tone} ${area.text}`}>
      {/* Text links (wächst), rechts eine eigene Spalte mit Zahl und Hydra-Kopf – der Kopf überdeckt nie Text. */}
      <div className="flex min-w-0 flex-1 flex-col">
        <Icon size={24} className="sm:h-7 sm:w-7" />
        <h2 className="mt-2 text-[15px] font-black leading-tight text-[#e8eef8] sm:mt-3 sm:text-lg">{area.title}</h2>
        <p className="mt-0.5 text-xs text-[#9aa7bc]">{area.blurb}</p>
        <p className="mt-auto hidden truncate pt-3 text-[11px] text-[#9aa7bc] sm:block">{items.slice(0, 4).map(label).join(" · ")}{items.length > 4 ? " …" : ""}</p>
      </div>
      <div className="-mb-3 -mr-1 ml-1 flex shrink-0 flex-col items-end justify-between sm:-mb-4 sm:ml-2">
        <span className="rounded-full border border-current/30 px-2 py-0.5 text-[11px] font-bold opacity-80">{items.length}</span>
        <img src={area.head} alt="" aria-hidden="true" loading="lazy" draggable={false}
          className="pointer-events-none mt-1 h-[52px] w-auto select-none drop-shadow-[0_4px_10px_rgba(0,0,0,0.5)] transition duration-300 group-hover:-translate-y-1 group-hover:rotate-[-4deg] sm:h-[76px]" />
      </div>
    </button>
  )
}

function AppTile({ item, label, area, onOpen }: { item: NavItem; label: string; area: FilledArea; onOpen: () => void }) {
  const Icon = item.icon
  return (
    <button type="button" onClick={onOpen}
      className={`flex min-h-[96px] flex-col items-start justify-between rounded-[8px] border bg-gradient-to-br to-s-box p-3 text-left transition hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/40 ${area.area.tone} ${area.area.text}`}>
      <Icon size={22} />
      <span className="mt-2 w-full truncate text-sm font-bold text-[#e8eef8]">{label}</span>
      <span className="w-full truncate text-[11px] text-[#9aa7bc]">{area.area.title}</span>
    </button>
  )
}
