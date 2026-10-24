// VORSCHAU Startdesktop (Task 7876c5df): Kachel-Start mit Gruppen. Ändert nichts am echten Menü
// oder an der Startseite – erreichbar nur unter /start-vorschau.
import { useMemo } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { ArrowLeft, Search } from "lucide-react"
import { useState } from "react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { useMyAccess } from "@/features/access/useMyAccess"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { visibleItems, type NavItem } from "@/shared/nav-config"
import { navLabel } from "@/shared/nav-label"
import { EXTRA_ITEMS, fillGroups, type FilledGroup } from "./startLogic"
import { LABELS } from "./groups"

function greeting(now: Date): string {
  const h = now.getHours()
  return h < 11 ? "Guten Morgen" : h < 18 ? "Hallo" : "Guten Abend"
}

export function StartDeskPage() {
  const { t } = useTranslation("nav")
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const role = useAuthStore((s) => s.role)
  const username = useAuthStore((s) => s.username)
  const access = useMyAccess()
  const [query, setQuery] = useState("")
  const groups = useMemo(
    () => fillGroups([...visibleItems(role, access), ...(role === "admin" ? EXTRA_ITEMS : [])], role === "admin"),
    [role, access],
  )
  const openId = params.get("gruppe")
  const open = groups.find((g) => g.group.id === openId) ?? null
  const label = (i: NavItem) => LABELS[i.path] ?? navLabel(t, i.labelKey)
  const hits = query.trim()
    ? groups.flatMap((g) => g.items.map((i) => ({ i, g }))).filter(({ i }) => label(i).toLowerCase().includes(query.trim().toLowerCase()))
    : []

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]">
      <CockpitTopbar active="start" context="Vorschau: Startseite" />
      <main className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
        <div className="mx-auto max-w-6xl">
          <p className="mb-3 inline-flex rounded-[4px] border border-amber-400/40 bg-amber-400/10 px-2 py-1 text-[11px] font-bold text-amber-200">
            Vorschau – nur zum Ausprobieren, ändert nichts
          </p>
          {open ? (
            <GroupView fg={open} label={label} onBack={() => setParams({})} onOpen={(p) => navigate(p)} />
          ) : (
            <>
              <h1 className="text-2xl font-black text-[#e8eef8] sm:text-3xl">{greeting(new Date())}{username ? `, ${username}` : ""}</h1>
              <p className="mt-1 text-sm text-[#8d9ab0]">Wohin möchtest du?</p>
              <label className="mt-4 flex max-w-xl items-center gap-2 rounded-[6px] border border-[#2a364b] bg-[#0d1420] px-3 py-2.5 focus-within:border-[#46617f]">
                <Search size={16} className="shrink-0 text-[#8d9ab0]" />
                <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="App suchen …" aria-label="App suchen"
                  className="min-w-0 flex-1 bg-transparent text-sm text-[#e8eef8] placeholder:text-[#5f6d84] focus:outline-none" />
              </label>
              {query.trim() ? (
                <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                  {hits.length === 0 && <p className="col-span-full text-sm text-[#8d9ab0]">Nichts gefunden.</p>}
                  {hits.map(({ i, g }) => <AppTile key={i.path} item={i} label={label(i)} tone={g.group.tone} hint={g.group.title} onOpen={() => navigate(i.path)} />)}
                </div>
              ) : (
                <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {groups.map((fg) => <GroupTile key={fg.group.id} fg={fg} label={label} onOpen={() => setParams({ gruppe: fg.group.id })} />)}
                </div>
              )}
            </>
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
      className={`group flex min-h-[150px] flex-col rounded-[8px] border bg-gradient-to-br to-[#111827] p-4 text-left transition hover:-translate-y-0.5 hover:shadow-xl hover:shadow-black/40 ${group.tone}`}>
      <div className="flex items-center justify-between">
        <Icon size={28} />
        <span className="rounded-full border border-current/30 px-2 py-0.5 text-[11px] font-bold opacity-80">{items.length}</span>
      </div>
      <h2 className="mt-3 text-lg font-black text-[#e8eef8]">{group.title}</h2>
      <p className="mt-0.5 text-xs text-[#8d9ab0]">{group.blurb}</p>
      <p className="mt-auto pt-3 truncate text-[11px] text-[#718097]">{items.slice(0, 4).map(label).join(" · ")}{items.length > 4 ? " …" : ""}</p>
    </button>
  )
}

function GroupView({ fg, label, onBack, onOpen }: { fg: FilledGroup; label: (i: NavItem) => string; onBack: () => void; onOpen: (p: string) => void }) {
  const Icon = fg.group.icon
  return (
    <>
      <button type="button" onClick={onBack} className="mb-4 inline-flex items-center gap-1.5 rounded-[4px] border border-[#2a364b] bg-[#111827] px-3 py-1.5 text-sm font-bold text-[#cdd7e6] hover:border-[#46617f]">
        <ArrowLeft size={14} /> Alle Bereiche
      </button>
      <div className={`flex items-center gap-3 ${fg.group.tone.split(" ").filter((c) => c.startsWith("text-")).join(" ")}`}>
        <Icon size={30} />
        <div>
          <h1 className="text-2xl font-black text-[#e8eef8]">{fg.group.title}</h1>
          <p className="text-sm text-[#8d9ab0]">{fg.group.blurb}</p>
        </div>
      </div>
      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {fg.items.map((i) => <AppTile key={i.path} item={i} label={label(i)} tone={fg.group.tone} onOpen={() => onOpen(i.path)} />)}
      </div>
    </>
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
