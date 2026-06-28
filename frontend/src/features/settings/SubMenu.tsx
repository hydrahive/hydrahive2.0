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
      <div className="border-b border-white/8 px-4 py-3">
        <h2 className="text-sm font-semibold text-zinc-200">{group.submenuLabel ?? group.label}</h2>
      </div>
      <div className="flex-1 space-y-0.5 p-2">
        {loading ? (
          <div className="h-20 rounded-lg bg-zinc-900/50 animate-pulse" />
        ) : items.length === 0 ? (
          <p className="px-3 py-3 text-xs text-zinc-600">Keine Einträge.</p>
        ) : (
          items.map((it) => (
            <button
              key={it.id}
              onClick={() => onSelect(it.id)}
              className={`w-full truncate rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                activeItem === it.id
                  ? "bg-[#104E8B]/25 text-sky-200"
                  : "text-zinc-300 hover:bg-white/[5%]"
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
