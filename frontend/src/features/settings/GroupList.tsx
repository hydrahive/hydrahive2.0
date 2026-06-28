import { SETTINGS_GROUPS, type SettingsGroup } from "./registry"

interface Props {
  role: string
  activeId: string
  onSelect: (g: SettingsGroup) => void
}

/** Linke Spalte: alle Settings-Hauptgruppen, logisch geordnet. */
export function GroupList({ role, activeId, onSelect }: Props) {
  const groups = SETTINGS_GROUPS.filter((g) => !g.adminOnly || role === "admin")

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="border-b border-white/8 px-4 py-3">
        <h2 className="text-sm font-semibold text-zinc-200">Einstellungen</h2>
        <p className="text-[11px] text-zinc-500">Gruppe wählen</p>
      </div>
      <nav className="flex-1 space-y-0.5 p-2">
        {groups.map((g) => {
          const Icon = g.icon
          const active = g.id === activeId
          return (
            <button
              key={g.id}
              onClick={() => onSelect(g)}
              className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                active
                  ? "bg-[#104E8B]/25 text-sky-200 ring-1 ring-inset ring-[#104E8B]/50"
                  : "text-zinc-300 hover:bg-white/[5%]"
              }`}
            >
              <Icon size={15} className="shrink-0" />
              <span className="truncate">{g.label}</span>
            </button>
          )
        })}
      </nav>
    </div>
  )
}
