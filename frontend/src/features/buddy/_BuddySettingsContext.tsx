import type { BuddyConfig, BuddyConfigPatch } from "./api"

interface Props {
  config: BuddyConfig
  draft: BuddyConfigPatch
  onChange: (patch: BuddyConfigPatch) => void
}

export function BuddySettingsContext({ config, draft, onChange }: Props) {
  const context = draft.context ?? config.context

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-zinc-400">
          Was soll Buddy über dich wissen?
        </label>
        <textarea
          value={context}
          onChange={(e) => onChange({ context: e.target.value })}
          rows={12}
          placeholder={"Beispiel:\nIch bin Till, 35, Softwareentwickler.\nIch arbeite hauptsächlich mit Python und TypeScript.\nMeine laufenden Projekte: HydraHive2 (selbst gehostetes KI-System).\nIch habe ~4000 E-Books und eine große Filmsammlung.\nMeine bevorzugte Sprache ist Deutsch."}
          className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm placeholder:text-zinc-700 resize-none font-mono leading-relaxed"
        />
        <div className="flex items-center justify-between">
          <p className="text-xs text-zinc-600">
            Dieser Text wird in jeden Chat injiziert — Buddy kennt ihn immer.
          </p>
          <span className="text-xs text-zinc-700 font-mono">{context.length} / 8000</span>
        </div>
      </div>

      <div className="rounded-lg border border-amber-500/20 bg-amber-500/[4%] px-3 py-2">
        <p className="text-xs text-amber-400/80">
          Änderungen hier starten eine neue Chat-Session (neuer System-Prompt).
        </p>
      </div>
    </div>
  )
}
