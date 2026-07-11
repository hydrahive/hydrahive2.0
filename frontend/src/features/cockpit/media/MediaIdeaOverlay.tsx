import { useEffect, useState } from "react"
import type { MediaProject } from "../mediaProjectsApi"
import { CockpitButton } from "../CockpitButton"
import { CockpitSectionLabel } from "../CockpitPanel"

export function MediaIdeaOverlay({ project, onSave, onClose }: {
  project: MediaProject
  onSave: (input: { name: string; description: string }) => Promise<void>
  onClose: () => void
}) {
  const [name, setName] = useState(project.name)
  const [description, setDescription] = useState(project.description)
  const [status, setStatus] = useState("")

  useEffect(() => { setName(project.name); setDescription(project.description) }, [project])

  async function save() {
    if (!name.trim()) { setStatus("Bitte einen Projektnamen eingeben."); return }
    try { await onSave({ name: name.trim(), description: description.trim() }); setStatus("Idee gespeichert") }
    catch { setStatus("Speichern fehlgeschlagen") }
  }

  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/80 p-4" role="dialog" aria-modal="true" aria-labelledby="media-idea-title">
    <section className="w-full max-w-3xl overflow-hidden rounded-[4px] border border-[#46617f] bg-[#151c2b] shadow-2xl">
      <header className="flex items-center justify-between border-b border-[#2a364b] p-4"><div><CockpitSectionLabel>Idee</CockpitSectionLabel><h2 id="media-idea-title" className="mt-1 text-lg font-semibold text-[#e8eef8]">Projekt-Steckbrief</h2></div><CockpitButton onClick={onClose}>Schließen</CockpitButton></header>
      <main className="space-y-4 p-4"><label className="block text-xs text-[#8d9ab0]">Arbeitstitel<input autoFocus value={name} onChange={(event) => setName(event.target.value)} className="mt-1 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]" /></label><label className="block text-xs text-[#8d9ab0]">Grundidee, Ziel, Format und Ton<textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={12} placeholder="Worum geht es? Für wen entsteht das Projekt? Welches Format, Genre und welche Stimmung sind geplant?" className="mt-1 w-full resize-y rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm leading-6 text-[#e8eef8]" /></label><p className="text-xs text-[#8d9ab0]">Dieser Steckbrief gehört zum Media-Projekt. Er startet weder einen Agenten noch eine Generierung.</p>{status && <p className="text-sm text-[#69d7ff]">{status}</p>}</main>
      <footer className="flex justify-end border-t border-[#2a364b] p-3"><CockpitButton tone="primary" onClick={save}>Idee speichern</CockpitButton></footer>
    </section>
  </div>
}
