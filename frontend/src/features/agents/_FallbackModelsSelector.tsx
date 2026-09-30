import { useMemo } from "react"
import type { RegistryModel } from "@/features/llm/api"
import { providerName } from "@/features/llm/_llm_providers"

/**
 * Fallback-Modelle wählen: ein Dropdown pro Anbieter.
 * Gruppiert über das provider-Feld des Katalogs, nicht über den Präfix der id.
 * Der Präfix passt nicht immer (Anthropic ohne Präfix, NVIDIA als „nvidia_nim/“),
 * Task f17cb519.
 */
export function FallbackModelsSelector({ primary, catalog, selected, onChange }: {
  primary: string; catalog: RegistryModel[]; selected: string[]; onChange: (s: string[]) => void
}) {
  const add = (m: string) => onChange([...selected, m])
  const remove = (m: string) => onChange(selected.filter((x) => x !== m))
  const moveUp = (i: number) => {
    if (i === 0) return
    const next = [...selected]
    ;[next[i - 1], next[i]] = [next[i], next[i - 1]]
    onChange(next)
  }

  // Verbleibende Modelle nach Anbieter gruppieren → ein Dropdown pro Anbieter
  // (statt hunderte Buttons untereinander).
  const byProvider = useMemo(() => {
    const map = new Map<string, string[]>()
    for (const m of catalog) {
      if (m.id === primary || selected.includes(m.id)) continue
      const p = m.provider || "unknown"
      ;(map.get(p) ?? map.set(p, []).get(p)!).push(m.id)
    }
    return [...map.entries()]
      .map(([prov, ms]) => ({ prov, name: providerName(prov), ms }))
      .sort((a, b) => a.name.localeCompare(b.name))
  }, [catalog, primary, selected])

  return (
    <div className="space-y-2">
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selected.map((m, i) => (
            <span key={m} className="inline-flex items-center gap-1 pl-2.5 pr-1 py-1 rounded-md bg-violet-500/15 border border-violet-500/30 text-violet-200 text-xs font-mono">
              <span className="text-[10px] text-violet-400 mr-0.5">{i + 1}.</span>
              {m}
              <button onClick={() => moveUp(i)} disabled={i === 0}
                className="px-1 text-violet-300 hover:text-white disabled:opacity-30" title="hoch">↑</button>
              <button onClick={() => remove(m)}
                className="px-1 text-violet-300 hover:text-rose-300" title="entfernen">×</button>
            </span>
          ))}
        </div>
      )}
      {byProvider.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
          {byProvider.map(({ prov, name, ms }) => (
            <select
              key={prov}
              value=""
              onChange={(e) => { if (e.target.value) add(e.target.value) }}
              className="w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-300"
            >
              <option value="">+ {name} ({ms.length})…</option>
              {ms.map((m) => (
                <option key={m} value={m}>{m.includes("/") ? m.split("/").slice(1).join("/") : m}</option>
              ))}
            </select>
          ))}
        </div>
      ) : (
        selected.length === 0 && <p className="text-xs text-zinc-600">—</p>
      )}
    </div>
  )
}
