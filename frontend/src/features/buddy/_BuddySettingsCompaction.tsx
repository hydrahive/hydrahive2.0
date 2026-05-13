import type { BuddyConfig, BuddyConfigPatch } from "./api"

interface Props {
  config: BuddyConfig
  draft: BuddyConfigPatch
  onChange: (patch: BuddyConfigPatch) => void
  availableModels: string[]
}

export function BuddySettingsCompaction({ config, draft, onChange, availableModels }: Props) {
  const threshold = draft.compact_threshold_pct ?? config.compact_threshold_pct
  const model = draft.compact_model ?? config.compact_model
  const maxChars = draft.tool_result_max_chars ?? config.tool_result_max_chars

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs font-medium text-zinc-400">Compaction-Trigger</label>
          <span className="text-xs font-mono text-zinc-300">{threshold}%</span>
        </div>
        <input
          type="range"
          min={20}
          max={95}
          step={5}
          value={threshold}
          onChange={(e) => onChange({ compact_threshold_pct: Number(e.target.value) })}
          className="w-full accent-violet-500"
        />
        <p className="text-xs text-zinc-600">
          Compaction startet wenn der Context zu {threshold}% gefüllt ist. Niedriger = früher, sicherer.
        </p>
      </div>

      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-zinc-400">Compact-Modell</label>
        <select
          value={model}
          onChange={(e) => onChange({ compact_model: e.target.value })}
          className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm"
        >
          <option value="">Wie Hauptmodell ({config.model})</option>
          {availableModels.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <p className="text-xs text-zinc-600">
          Für Compaction reicht ein günstigeres Modell (z.B. claude-haiku).
        </p>
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="text-xs font-medium text-zinc-400">Tool-Result-Limit</label>
          <span className="text-xs font-mono text-zinc-500">{maxChars === 0 ? "kein Limit" : `${maxChars} Zeichen`}</span>
        </div>
        <input
          type="number"
          min={0}
          step={1000}
          value={maxChars}
          onChange={(e) => onChange({ tool_result_max_chars: Number(e.target.value) })}
          placeholder="0 = kein Limit"
          className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm"
        />
        <p className="text-xs text-zinc-600">
          Kürzt Tool-Ergebnisse auf X Zeichen bevor sie in den Context gehen. 0 = kein Limit. Empfehlung: 12000.
        </p>
      </div>
    </div>
  )
}
