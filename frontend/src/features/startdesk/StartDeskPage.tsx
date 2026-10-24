// VORSCHAU Startdesktop (Task 7876c5df): Kachel-Start. Klick auf einen Bereich öffnet direkt dessen
// zuletzt benutzte (sonst erste) App; oben zeigt die Bereichs-Leiste dann nur diesen Bereich.
// Erreichbar unter /start-vorschau; die Bereichs-Leiste lässt sich hier ein- und ausschalten.
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Search } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import type { NavItem } from "@/shared/nav-config"
import { entryPath, setPreviewOn, storeArea } from "./areaState"
import type { FilledGroup } from "./startLogic"
import { useAreas } from "./useAreas"
import { usePreviewOn } from "./usePreviewOn"

function greeting(now: Date): string {
  const h = now.getHours()
  return h < 11 ? "Guten Morgen" : h < 18 ? "Hallo" : "Guten Abend"
}

export function StartDeskPage() {
  const navigate = useNavigate()
  const username = useAuthStore((s) => s.username)
  const { groups, label } = useAreas()
  const preview = usePreviewOn()
  const [query, setQuery] = useState("")
  const needle = query.trim().toLowerCase()
  const hits = needle ? groups.flatMap((g) => g.items.map((i) => ({ i, g }))).filter(({ i }) => label(i).toLowerCase().includes(needle)) : []
  const openArea = (fg: FilledGroup) => { storeArea(fg.group.id); navigate(entryPath(fg)) }

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]">
      <CockpitTopbar active="start" context="Vorschau: Startseite" />
      <main className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
        <div className="mx-auto max-w-6xl">
          <div className="mb-3 flex flex-wrap items-center gap-2 rounded-[6px] border border-amber-400/40 bg-amber-400/10 px-3 py-2 text-xs text-amber-100">
            <span className="font-bold">Vorschau</span>
            <span className="text-amber-200/80">– nur in diesem Browser, ändert nichts für andere.</span>
            <label className="ml-auto flex cursor-pointer items-center gap-2 font-bold">
              <input type="checkbox" checked={preview} onChange={(e) => setPreviewOn(e.target.checked)} className="h-4 w-4 accent-amber-400" />
              Neue Bereichs-Leiste oben
            </label>
          </div>
          <h1 className="text-xl font-black text-[#e8eef8] sm:text-3xl">{greeting(new Date())}{username ? `, ${username}` : ""}</h1>
          <p className="mt-1 text-sm text-[#8d9ab0]">Wohin möchtest du?</p>
          <label className="mt-4 flex max-w-xl items-center gap-2 rounded-[6px] border border-[#2a364b] bg-[#0d1420] px-3 py-2.5 focus-within:border-[#46617f]">
            <Search size={16} className="shrink-0 text-[#8d9ab0]" />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="App suchen …" aria-label="App suchen"
              onKeyDown={(e) => { if (e.key === "Enter" && hits[0]) navigate(hits[0].i.path) }}
              className="min-w-0 flex-1 bg-transparent text-sm text-[#e8eef8] placeholder:text-[#5f6d84] focus:outline-none" />
          </label>
          {needle ? (
            <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {hits.length === 0 && <p className="col-span-full text-sm text-[#8d9ab0]">Nichts gefunden.</p>}
              {hits.map(({ i, g }) => <AppTile key={i.path} item={i} label={label(i)} tone={g.group.tone} hint={g.group.title} onOpen={() => navigate(i.path)} />)}
            </div>
          ) : (
            <div className="mt-5 grid grid-cols-2 gap-2.5 sm:gap-3 lg:grid-cols-4">
              {groups.map((fg) => <GroupTile key={fg.group.id} fg={fg} label={label} onOpen={() => openArea(fg)} />)}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

function GroupTile({ fg, label, onOpen }: { fg: FilledGroup; label: (i: NavItem) => string; onOpen: () => void }) {
  const { group, items } = fg
  const Icon = group.icon
  return (
    <button type="button" onClick={onOpen}
      className={`group flex min-h-[118px] flex-col rounded-[8px] border bg-gradient-to-br to-[#111827] p-3 text-left transition hover:-translate-y-0.5 hover:shadow-xl hover:shadow-black/40 sm:min-h-[150px] sm:p-4 ${group.tone}`}>
      <div className="flex items-center justify-between">
        <Icon size={24} className="sm:h-7 sm:w-7" />
        <span className="rounded-full border border-current/30 px-2 py-0.5 text-[11px] font-bold opacity-80">{items.length}</span>
      </div>
      <h2 className="mt-2 text-[15px] font-black leading-tight text-[#e8eef8] sm:mt-3 sm:text-lg">{group.title}</h2>
      <p className="mt-0.5 text-xs text-[#8d9ab0]">{group.blurb}</p>
      <p className="mt-auto hidden truncate pt-3 text-[11px] text-[#718097] sm:block">{items.slice(0, 4).map(label).join(" · ")}{items.length > 4 ? " …" : ""}</p>
    </button>
  )
}

function AppTile({ item, label, tone, hint, onOpen }: { item: NavItem; label: string; tone: string; hint?: string; onOpen: () => void }) {
  const Icon = item.icon
  return (
    <button type="button" onClick={onOpen}
      className={`flex min-h-[96px] flex-col items-start justify-between rounded-[8px] border bg-gradient-to-br to-[#111827] p-3 text-left transition hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/40 ${tone}`}>
      <Icon size={22} />
      <span className="mt-2 w-full truncate text-sm font-bold text-[#e8eef8]">{label}</span>
      {hint && <span className="w-full truncate text-[11px] text-[#718097]">{hint}</span>}
    </button>
  )
}
