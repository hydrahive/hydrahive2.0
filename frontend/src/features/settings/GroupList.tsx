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
      <div className="border-b border-[#2a364b] px-3 py-3">
        <p className="mb-1 inline-flex rounded-[4px] border border-[#69d7ff]/35 bg-[#1c2940] px-2 py-1 text-[10px] font-black uppercase tracking-[0.14em] text-[#69d7ff]">System</p>
        <h2 className="text-sm font-bold text-[#e8eef8]">Einstellungen</h2>
        <p className="text-[11px] text-[#8d9ab0]">Gruppe wählen</p>
      </div>
      <nav className="flex-1 space-y-0.5 p-2">
        {groups.map((g) => {
          const Icon = g.icon
          const active = g.id === activeId
          return (
            <button
              key={g.id}
              onClick={() => onSelect(g)}
              className={`flex w-full items-center gap-2 rounded-[4px] border px-3 py-2 text-left text-sm transition-colors ${
                active
                  ? "border-[#69d7ff]/40 bg-[#1c2940] font-semibold text-[#69d7ff]"
                  : "border-transparent text-[#8d9ab0] hover:border-[#2a364b] hover:bg-[#151c2b] hover:text-[#e8eef8]"
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
