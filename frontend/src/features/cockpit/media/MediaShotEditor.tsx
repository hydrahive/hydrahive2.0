import type { MediaAssetReference } from "../mediaProjectsApi"
import type { MediaShot } from "../mediaWorkspaceApi"
import { MediaAssetPicker } from "./MediaAssetPicker"
import { clampDuration, toggleReference } from "./shotUpdates"

export function MediaShotEditor({ shot, references, onChange, onRemove }: {
  shot: MediaShot
  references: MediaAssetReference[]
  onChange: (changes: Partial<MediaShot>) => void
  onRemove: () => void
}) {
  const characters = references.filter((asset) => asset.kind === "character")
  const assets = references.filter((asset) => asset.kind !== "character")
  const field = "w-full rounded-[3px] border border-[#2a364b] bg-[#101724] px-2 py-1.5 text-xs text-[#e8eef8] outline-none focus:border-[#46617f]"

  return <article className="space-y-3 rounded-[4px] border border-[#2a364b] bg-[#151c2b] p-3">
    <div className="flex gap-2"><label className="min-w-0 flex-1 text-[10px] uppercase tracking-wider text-[#718097]">Shot-Titel<input value={shot.title} onChange={(event) => onChange({ title: event.target.value })} className={`${field} mt-1 text-sm font-semibold`} /></label><button type="button" onClick={onRemove} className="self-end rounded-[3px] border border-rose-500/30 px-2 py-1.5 text-xs text-rose-300 hover:bg-rose-500/10">Entfernen</button></div>
    <label className="block text-[10px] uppercase tracking-wider text-[#718097]">Beschreibung<textarea value={shot.description} onChange={(event) => onChange({ description: event.target.value })} rows={3} className={`${field} mt-1 resize-y`} /></label>
    <div className="grid gap-2 sm:grid-cols-[130px_1fr]"><label className="text-[10px] uppercase tracking-wider text-[#718097]">Dauer (Sek.)<input type="number" min="0.1" max="3600" step="0.1" value={shot.duration} onChange={(event) => onChange({ duration: clampDuration(event.target.valueAsNumber) })} className={`${field} mt-1`} /></label><label className="text-[10px] uppercase tracking-wider text-[#718097]">Kamera<input value={shot.camera} onChange={(event) => onChange({ camera: event.target.value })} placeholder="z. B. Totale, langsamer Dolly-in" className={`${field} mt-1`} /></label></div>
    <label className="block text-[10px] uppercase tracking-wider text-[#718097]">Dialog / Voiceover<textarea value={shot.dialogue} onChange={(event) => onChange({ dialogue: event.target.value })} rows={2} className={`${field} mt-1 resize-y`} /></label>
    <fieldset><legend className="mb-2 text-[10px] uppercase tracking-wider text-[#718097]">Charaktere</legend><MediaAssetPicker assets={characters} selected={shot.character_ids} onToggle={(id) => onChange({ character_ids: toggleReference(shot.character_ids, id) })} emptyLabel="Noch keine Charakter-Referenzen im Media-Projekt." /></fieldset>
    <fieldset><legend className="mb-2 text-[10px] uppercase tracking-wider text-[#718097]">Assets</legend><MediaAssetPicker assets={assets} selected={shot.asset_ids} onToggle={(id) => onChange({ asset_ids: toggleReference(shot.asset_ids, id) })} emptyLabel="Noch keine Asset-Referenzen im Media-Projekt." /></fieldset>
  </article>
}
