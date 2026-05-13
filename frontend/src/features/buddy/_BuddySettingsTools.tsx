import type { BuddyConfig, BuddyConfigPatch } from "./api"

interface Props {
  config: BuddyConfig
  draft: BuddyConfigPatch
  onChange: (patch: BuddyConfigPatch) => void
}

export function BuddySettingsTools({ config, draft, onChange }: Props) {
  const activeTools = new Set(draft.tools ?? config.tools)

  function toggle(tool: string) {
    const next = new Set(activeTools)
    if (next.has(tool)) next.delete(tool)
    else next.add(tool)
    onChange({ tools: Array.from(next) })
  }

  function toggleAll(enable: boolean) {
    onChange({ tools: enable ? [...config.all_tools] : [] })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-zinc-500">
          {activeTools.size} von {config.all_tools.length} Tools aktiv
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => toggleAll(true)}
            className="text-xs text-zinc-500 hover:text-zinc-300 px-2 py-1 rounded hover:bg-white/5"
          >
            Alle an
          </button>
          <button
            onClick={() => toggleAll(false)}
            className="text-xs text-zinc-500 hover:text-zinc-300 px-2 py-1 rounded hover:bg-white/5"
          >
            Alle aus
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {config.all_tools.map((tool) => {
          const active = activeTools.has(tool)
          return (
            <button
              key={tool}
              onClick={() => toggle(tool)}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg border text-left transition-all ${
                active
                  ? "border-violet-500/40 bg-violet-500/[6%] text-violet-300"
                  : "border-white/[6%] bg-zinc-950 text-zinc-600 hover:border-white/10 hover:text-zinc-500"
              }`}
            >
              <div className={`w-2 h-2 rounded-full shrink-0 ${active ? "bg-violet-400" : "bg-zinc-700"}`} />
              <span className="text-xs font-mono truncate">{tool}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
