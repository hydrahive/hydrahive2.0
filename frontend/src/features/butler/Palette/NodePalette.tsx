import { useState } from "react"
import { Bell, Filter, Search, Zap } from "lucide-react"
import type { NodeType, RegistryMeta, SpecMeta } from "../types"

const ICONS = { trigger: Bell, condition: Filter, action: Zap }
const COLORS = {
  trigger: "border-emerald-500/30 hover:bg-emerald-500/10",
  condition: "border-sky-500/30 hover:bg-sky-500/10",
  action: "border-amber-500/30 hover:bg-amber-500/10",
}

interface Props {
  registry: RegistryMeta
}

export function NodePalette({ registry }: Props) {
  const [q, setQ] = useState("")

  function filter(specs: SpecMeta[]): SpecMeta[] {
    if (!q.trim()) return specs
    const ql = q.toLowerCase()
    return specs.filter((s) =>
      s.subtype.toLowerCase().includes(ql) ||
      s.label.toLowerCase().includes(ql) ||
      s.description.toLowerCase().includes(ql)
    )
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-2 border-b border-white/[8%] flex-shrink-0">
        <div className="relative">
          <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Suchen…"
            className="w-full pl-7 pr-2 py-1 text-xs bg-white/[3%] border border-white/[8%] rounded-md placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50" />
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-auto px-3 py-3 space-y-4">
        <Group title="Trigger" specs={filter(registry.triggers)} type="trigger" />
        <Group title="Bedingungen" specs={filter(registry.conditions)} type="condition" />
        <Group title="Aktionen" specs={filter(registry.actions)} type="action" />
      </div>
    </div>
  )
}

function Group({ title, specs, type }: { title: string; specs: SpecMeta[]; type: NodeType }) {
  if (specs.length === 0) return null
  const Icon = ICONS[type]
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-1.5">
        <Icon size={11} className="text-zinc-400" />
        <p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">{title}</p>
      </div>
      <div className="space-y-1.5">
        {specs.map((s) => (
          <Item key={s.subtype} spec={s} type={type} />
        ))}
      </div>
    </div>
  )
}

function Item({ spec, type }: { spec: SpecMeta; type: NodeType }) {
  return (
    <div draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("application/butler-spec",
          JSON.stringify({ type, subtype: spec.subtype }))
        e.dataTransfer.effectAllowed = "move"
      }}
      className={`px-2 py-1.5 rounded-md border bg-white/[2%] cursor-grab active:cursor-grabbing transition-colors ${COLORS[type]}`}>
      <p className="text-xs font-semibold text-zinc-100">{spec.label}</p>
      <p className="text-[10px] text-zinc-500 mt-0.5 line-clamp-2">{spec.description}</p>
    </div>
  )
}
