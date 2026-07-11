import { useEffect, useState } from "react"
import { mediaAssetsApi, type MediaAssetReference } from "./mediaProjectsApi"
import { mediaWorkspaceApi, type MediaScreenplay, type MediaShot } from "./mediaWorkspaceApi"
import { MediaShotEditor } from "./media/MediaShotEditor"
import { updateShot } from "./media/shotUpdates"
import { CockpitButton } from "./CockpitButton"
import { CockpitSectionLabel } from "./CockpitPanel"

const empty: MediaScreenplay = { title: "", logline: "", acts: [] }
const makeId = (prefix: string) => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
const newShot = (): MediaShot => ({ id: makeId("shot"), title: "Neuer Shot", description: "", duration: 5, camera: "", character_ids: [], asset_ids: [], dialogue: "" })

export function MediaScreenplayOverlay({ projectId, mediaSlug, onClose }: { projectId: string; mediaSlug: string; onClose: () => void }) {
  const [value, setValue] = useState<MediaScreenplay>(empty)
  const [references, setReferences] = useState<MediaAssetReference[]>([])
  const [message, setMessage] = useState("Lädt…")

  useEffect(() => {
    Promise.all([mediaWorkspaceApi.getScreenplay(projectId, mediaSlug), mediaAssetsApi.list(projectId, mediaSlug)])
      .then(([screenplay, assets]) => { setValue(screenplay); setReferences(assets); setMessage("Regie und Referenzen geladen") })
      .catch(() => setMessage("Regie oder Referenzen nicht erreichbar"))
  }, [projectId, mediaSlug])

  async function save() {
    try { setValue(await mediaWorkspaceApi.saveScreenplay(projectId, mediaSlug, value)); setMessage("Gespeichert") }
    catch { setMessage("Speichern fehlgeschlagen") }
  }

  function updateScene(ai: number, si: number, changes: { title?: string; description?: string }) {
    setValue((old) => ({ ...old, acts: old.acts.map((act, x) => x === ai ? { ...act, scenes: act.scenes.map((scene, y) => y === si ? { ...scene, ...changes } : scene) } : act) }))
  }

  function removeShot(ai: number, si: number, hi: number) {
    setValue((old) => ({ ...old, acts: old.acts.map((act, x) => x === ai ? { ...act, scenes: act.scenes.map((scene, y) => y === si ? { ...scene, shots: scene.shots.filter((_, z) => z !== hi) } : scene) } : act) }))
  }

  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/80 p-4" role="dialog" aria-modal="true" aria-labelledby="screenplay-title">
    <section className="flex h-[min(860px,95dvh)] w-full max-w-7xl flex-col overflow-hidden rounded-[4px] border border-[#46617f] bg-[#151c2b]">
      <header className="flex items-center justify-between border-b border-[#2a364b] p-4"><div><CockpitSectionLabel>Regie</CockpitSectionLabel><h2 id="screenplay-title" className="text-lg font-semibold text-[#e8eef8]">Akt → Szene → Shot</h2></div><div className="flex gap-2"><CockpitButton onClick={onClose}>Schließen</CockpitButton><CockpitButton tone="primary" onClick={save}>Speichern</CockpitButton></div></header>
      <div className="grid gap-3 border-b border-[#2a364b] p-4 md:grid-cols-2"><TextField label="Filmtitel" value={value.title} onChange={(title) => setValue({ ...value, title })} /><TextField label="Logline" value={value.logline} onChange={(logline) => setValue({ ...value, logline })} /></div>
      <main className="min-h-0 flex-1 overflow-y-auto p-4"><div className="space-y-4">{value.acts.map((act, ai) => <section key={act.id} className="rounded-[4px] border border-[#2a364b] bg-[#101724] p-3"><div className="flex flex-wrap gap-2"><input value={act.title} onChange={(event) => setValue((old) => ({ ...old, acts: old.acts.map((item, index) => index === ai ? { ...item, title: event.target.value } : item) }))} className="min-w-48 flex-1 bg-transparent font-semibold text-[#e8eef8] outline-none" /><CockpitButton onClick={() => setValue((old) => ({ ...old, acts: old.acts.filter((_, index) => index !== ai) }))}>Akt löschen</CockpitButton><CockpitButton onClick={() => setValue((old) => ({ ...old, acts: old.acts.map((item, index) => index === ai ? { ...item, scenes: [...item.scenes, { id: makeId("scene"), title: "Neue Szene", description: "", shots: [] }] } : item) }))}>Szene +</CockpitButton></div><div className="mt-3 space-y-3">{act.scenes.map((scene, si) => <article key={scene.id} className="rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-3"><input value={scene.title} onChange={(event) => updateScene(ai, si, { title: event.target.value })} className="w-full bg-transparent text-sm font-semibold text-[#e8eef8] outline-none" /><textarea value={scene.description} onChange={(event) => updateScene(ai, si, { description: event.target.value })} placeholder="Szenenbeschreibung" className="mt-2 w-full rounded-[3px] border border-[#2a364b] bg-[#111827] p-2 text-xs text-[#d7deea]" /><div className="my-3 flex justify-end"><CockpitButton onClick={() => setValue((old) => ({ ...old, acts: old.acts.map((item, x) => x === ai ? { ...item, scenes: item.scenes.map((entry, y) => y === si ? { ...entry, shots: [...entry.shots, newShot()] } : entry) } : item) }))}>Shot +</CockpitButton></div><div className="grid gap-3 xl:grid-cols-2">{scene.shots.map((shot, hi) => <MediaShotEditor key={shot.id} shot={shot} references={references} onChange={(changes) => setValue((old) => updateShot(old, ai, si, hi, changes))} onRemove={() => removeShot(ai, si, hi)} />)}</div></article>)}</div></section>)}</div><CockpitButton onClick={() => setValue((old) => ({ ...old, acts: [...old.acts, { id: makeId("act"), title: `Akt ${old.acts.length + 1}`, scenes: [] }] }))} className="mt-4">Akt hinzufügen</CockpitButton></main>
      <footer className="border-t border-[#2a364b] p-3 text-xs text-[#8d9ab0]">{message} · Keine Generierung wird durch Speichern gestartet.</footer>
    </section>
  </div>
}

function TextField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="text-xs text-[#8d9ab0]">{label}<input value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-2 text-[#e8eef8]" /></label>
}
