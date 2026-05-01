import { Check } from "lucide-react"
import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import type { ToolMeta } from "./types"

interface Props {
  available: ToolMeta[]
  selected: string[]
  onChange: (next: string[]) => void
}

const ALL = "__all__"

export function ToolsSelector({ available, selected, onChange }: Props) {
  const { t } = useTranslation("agents")
  const [filter, setFilter] = useState<string>(ALL)
  const set = new Set(selected)

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
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-1">
        {visible.map((tool) => {
          const checked = set.has(tool.name)
          return (
            <button
              key={tool.name}
              type="button"
              onClick={() => toggle(tool.name)}
              title={tool.description}
              className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-left transition-all ${
                checked
                  ? "border-violet-500/40 bg-violet-500/[8%]"
                  : "border-white/[6%] bg-white/[2%] hover:bg-white/[4%]"
              }`}
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
              <p className="text-[11px] font-mono text-zinc-200 truncate">{tool.name}</p>
            </button>
          )
        })}
      </div>
    </div>
  )
}
