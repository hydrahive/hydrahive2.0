import { Check, X } from "lucide-react"
import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import type { ToolMeta } from "./types"

interface Props {
  available: ToolMeta[]
  selected: string[]
  onChange: (next: string[]) => void
  /** Werkzeuge, die der Besitzer nicht freigegeben hat (nur Anzeige). */
  blocked?: Set<string>
}

const ALL = "__all__"
const CATEGORY_PREFIX = "kategorie:"

export function ToolsSelector({ available, selected, onChange, blocked }: Props) {
  const { t } = useTranslation("agents")
  const [filter, setFilter] = useState<string>(ALL)
  const set = new Set(selected)
  // kategorie:x-Einträge (Katalog) stehen nicht in der Tool-Liste – sichtbar und entfernbar machen, sonst bleiben sie unsichtbar kleben.
  const categoryEntries = selected.filter((name) => name.startsWith(CATEGORY_PREFIX))

  const categories = useMemo(() => {
    const counts = new Map<string, number>()
    for (const tool of available) {
      const cat = tool.category ?? "other"
      counts.set(cat, (counts.get(cat) ?? 0) + 1)
    }
    return [...counts.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [available])

  const visible = useMemo(() => {
    if (filter === ALL) return available
    return available.filter((tool) => {
      if (set.has(tool.name)) return true
      return (tool.category ?? "other") === filter
    })
  }, [available, filter, selected])

  function toggle(name: string) {
    const next = new Set(set)
    if (next.has(name)) next.delete(name)
    else next.add(name)
    onChange(Array.from(next))
  }

  function categoryLabel(cat: string): string {
    if (cat.startsWith("plugin:")) return t("tool_categories.plugin", { name: cat.slice(7) })
    return t(`tool_categories.${cat}`, { defaultValue: cat })
  }

  return (
    <div className="space-y-1.5">
      {categoryEntries.length > 0 && (
        <div className="flex flex-wrap items-center gap-1" data-testid="category-entries">
          <span className="text-[10px] text-zinc-500">{t("category_entries.label")}</span>
          {categoryEntries.map((entry) => {
            const cat = entry.slice(CATEGORY_PREFIX.length)
            return (
              <button
                key={entry}
                type="button"
                onClick={() => toggle(entry)}
                title={t("category_entries.remove", { name: cat })}
                className="flex items-center gap-1 px-2 py-0.5 rounded-md border border-violet-500/40 bg-violet-500/[8%] text-[11px] font-mono text-zinc-200 hover:bg-violet-500/[15%]"
              >
                {entry}
                <X size={10} className="text-zinc-400" />
              </button>
            )
          })}
        </div>
      )}
      <select
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="w-full sm:w-64 px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"
      >
        <option value={ALL}>{t("tool_categories.all", { count: available.length })}</option>
        {categories.map(([cat, count]) => (
          <option key={cat} value={cat}>
            {categoryLabel(cat)} ({count})
          </option>
        ))}
      </select>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-1 max-h-56 overflow-y-auto pr-1">
        {visible.map((tool) => {
          const checked = set.has(tool.name)
          const isBlocked = blocked?.has(tool.name) ?? false
          return (
            <button
              key={tool.name}
              type="button"
              onClick={() => toggle(tool.name)}
              title={isBlocked ? `${t("tools_blocked_hint")}\n${tool.description}` : tool.description}
              className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-left transition-all ${
                checked
                  ? "border-violet-500/40 bg-violet-500/[8%]"
                  : "border-white/[6%] bg-white/[2%] hover:bg-white/[4%]"
              }${isBlocked ? " opacity-50" : ""}`}
            >
              <div
                className={`w-3.5 h-3.5 rounded flex items-center justify-center flex-shrink-0 transition-all ${
                  checked
                    ? "bg-gradient-to-br from-indigo-600 to-violet-600 shadow shadow-violet-900/20"
                    : "border border-zinc-600"
                }`}
              >
                {checked && <Check size={9} className="text-white" />}
              </div>
              <p className={`text-[11px] font-mono truncate ${isBlocked ? "text-zinc-500 line-through" : "text-zinc-200"}`}>{tool.name}</p>
            </button>
          )
        })}
      </div>
    </div>
  )
}
