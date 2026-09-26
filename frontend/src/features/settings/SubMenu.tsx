import { useEffect, useState } from "react"
import { api } from "@/shared/api-client"
import type { SettingsGroup } from "./registry"

interface Props {
  group: SettingsGroup
  activeItem: string | null
  onSelect: (id: string) => void
}

interface Entry { id: string; name: string }

/**
 * Rechte Spalte: kontextabhängiges Submenü. Bei "agenten" die Agenten, bei
 * "projekte" die Projekte. Wird nur gerendert, wenn group.hasSubmenu — sonst
 * blendet die Page diese Spalte komplett aus (Tills Vorgabe).
 */
export function SubMenu({ group, activeItem, onSelect }: Props) {
  const [items, setItems] = useState<Entry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const url = group.id === "agents" ? "/agents"
      : group.id === "projects" ? "/projects"
      : null
    if (!url) { setItems([]); setLoading(false); return }
    api.get<Array<{ id: string; name?: string; config?: { identity?: string } }>>(url)
      .then((res) => setItems((res || []).map((x) => ({
        id: x.id,
        name: x.config?.identity ? String(x.config.identity).slice(0, 28) : (x.name || x.id),
      }))))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [group.id])

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="border-b border-[#2a364b] px-3 py-3">
        <p className="mb-1 text-[10px] font-black uppercase tracking-[0.14em] text-[#69d7ff]">Auswahl</p>
        <h2 className="text-sm font-bold text-[#e8eef8]">{group.submenuLabel ?? group.label}</h2>
      </div>
      <div className="flex-1 space-y-0.5 p-2">
        {loading ? (
          <div className="h-20 rounded-[4px] border border-[#2a364b] bg-[#151c2b] animate-pulse" />
        ) : items.length === 0 ? (
          <p className="px-3 py-3 text-xs text-[#8d9ab0]">Keine Einträge.</p>
        ) : (
          items.map((it) => (
            <button
              key={it.id}
              onClick={() => onSelect(it.id)}
              className={`w-full truncate rounded-[4px] border px-3 py-2 text-left text-sm transition-colors ${
                activeItem === it.id
                  ? "border-[#69d7ff]/40 bg-[#1c2940] font-semibold text-[#69d7ff]"
                  : "border-transparent text-[#8d9ab0] hover:border-[#2a364b] hover:bg-[#151c2b] hover:text-[#e8eef8]"
              }`}
            >
              {it.name}
            </button>
          ))
        )}
      </div>
    </div>
  )
}
