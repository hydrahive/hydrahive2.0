import { Dice5 } from "lucide-react"
import type { BuddyConfig, BuddyConfigPatch } from "./api"

const LANGUAGE_OPTIONS = [
  { value: "de", label: "Immer Deutsch" },
  { value: "en", label: "Always English" },
  { value: "auto", label: "Folgt dem User" },
]
const TONE_OPTIONS = [
  { value: "locker", label: "Locker & direkt" },
  { value: "professionell", label: "Professionell" },
  { value: "knapp", label: "Kurz und knapp" },
]

interface Props {
  config: BuddyConfig
  draft: BuddyConfigPatch
  onChange: (patch: BuddyConfigPatch) => void
  onRerollCharacter: () => void
  busy: boolean
}

export function BuddySettingsIdentity({ config, draft, onChange, onRerollCharacter, busy }: Props) {
  const name = draft.name ?? config.name
  const language = draft.language ?? config.language
  const tone = draft.tone ?? config.tone

  return (
    <div className="space-y-6">
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-zinc-400">Name</label>
        <input
          value={name}
          onChange={(e) => onChange({ name: e.target.value })}
          className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm"
        />
      </div>

      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-zinc-400">Aktueller Charakter</label>
        <div className="flex items-center gap-3">
          <span className="flex-1 px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-300 text-sm truncate">
            {config.character || "—"}
          </span>
          <button
            onClick={onRerollCharacter}
            disabled={busy}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-white/[8%] text-xs text-zinc-400 hover:text-pink-300 hover:border-pink-500/30 hover:bg-pink-500/[4%] transition-all disabled:opacity-40"
          >
            <Dice5 size={13} />
            Würfeln
          </button>
        </div>
        <p className="text-xs text-zinc-600">Würfeln startet eine neue Chat-Session mit dem neuen Charakter.</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-400">Sprache</label>
          <select
            value={language}
            onChange={(e) => onChange({ language: e.target.value as BuddyConfigPatch["language"] })}
            className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm"
          >
            {LANGUAGE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-400">Ton</label>
          <select
            value={tone}
            onChange={(e) => onChange({ tone: e.target.value as BuddyConfigPatch["tone"] })}
            className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm"
          >
            {TONE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>

      <p className="text-xs text-zinc-600">
        Sprache und Ton ändern den System-Prompt. Eine neue Chat-Session wird automatisch gestartet.
      </p>
    </div>
  )
}
