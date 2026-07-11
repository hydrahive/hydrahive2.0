import { useEffect, useState } from "react"
import { projectsApi } from "@/features/projects/api"
import type { Project } from "@/features/projects/types"
import { CockpitButton } from "../CockpitButton"
import { CockpitSectionLabel } from "../CockpitPanel"

export function ProjectDetailsOverlay({ project, onClose, onSaved, onDeleted }: { project: Project; onClose: () => void; onSaved: (project: Project) => void; onDeleted: (projectId: string) => void }) {
  const [name, setName] = useState(project.name)
  const [description, setDescription] = useState(project.description)
  const [status, setStatus] = useState(project.status)
  const [notes, setNotes] = useState(project.notes)
  const [deleteName, setDeleteName] = useState("")
  const [deleting, setDeleting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  useEffect(() => { setName(project.name); setDescription(project.description); setStatus(project.status); setNotes(project.notes); setDeleteName(""); setError("") }, [project])
  const dirty = name.trim() !== project.name || description.trim() !== project.description || status !== project.status || notes !== project.notes

  const save = async () => {
    if (!name.trim() || !dirty || saving) return
    setSaving(true); setError("")
    try { onSaved(await projectsApi.update(project.id, { name: name.trim(), description: description.trim(), status, notes })) }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Projekt konnte nicht gespeichert werden.") }
    finally { setSaving(false) }
  }
  const remove = async () => {
    if (deleteName !== project.name || deleting) return
    setDeleting(true); setError("")
    try { await projectsApi.delete(project.id); onDeleted(project.id) }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Projekt konnte nicht gelöscht werden."); setDeleting(false) }
  }

  return <div className="fixed inset-0 z-[100] grid place-items-center bg-black/80 p-4" role="dialog" aria-modal="true" aria-labelledby="project-details-title"><section className="flex h-[min(780px,94dvh)] w-full max-w-3xl flex-col overflow-hidden rounded-[6px] border border-[#46617f] bg-[#151c2b] shadow-2xl"><header className="flex items-center justify-between border-b border-[#2a364b] p-4"><div><CockpitSectionLabel>Projektverwaltung</CockpitSectionLabel><h2 id="project-details-title" className="mt-1 text-lg font-semibold text-[#e8eef8]">Basisdaten & Notizen</h2></div><CockpitButton onClick={onClose} disabled={saving || deleting}>Schließen</CockpitButton></header><main className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4"><label className="block text-xs text-[#8d9ab0]">Projektname<input value={name} onChange={(event) => setName(event.target.value)} maxLength={200} className="mt-1 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]" /></label><label className="block text-xs text-[#8d9ab0]">Beschreibung<textarea value={description} onChange={(event) => setDescription(event.target.value)} maxLength={4000} rows={4} className="mt-1 w-full resize-y rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]" /></label><label className="block text-xs text-[#8d9ab0]">Status<select value={status} onChange={(event) => setStatus(event.target.value as Project["status"])} className="mt-1 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]"><option value="active">Aktiv</option><option value="paused">Pausiert</option><option value="archived">Archiviert</option></select></label><label className="block text-xs text-[#8d9ab0]">Notizen<textarea value={notes} onChange={(event) => setNotes(event.target.value)} maxLength={50_000} rows={9} className="mt-1 w-full resize-y rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm leading-5 text-[#e8eef8]" /></label>{error && <p className="rounded-[4px] border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</p>}<section className="rounded-[4px] border border-rose-500/30 bg-rose-500/[7%] p-4"><h3 className="text-sm font-semibold text-rose-200">Projekt endgültig löschen</h3><p className="mt-1 text-xs leading-5 text-rose-200/70">Workspace, Konfiguration und Projektzuordnungen werden entfernt. Zur Bestätigung exakt <strong>{project.name}</strong> eingeben.</p><div className="mt-3 flex gap-2"><input value={deleteName} onChange={(event) => setDeleteName(event.target.value)} className="min-w-0 flex-1 rounded-[4px] border border-rose-500/30 bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]" /><CockpitButton onClick={() => void remove()} disabled={deleteName !== project.name || deleting}>{deleting ? "Löscht…" : "Endgültig löschen"}</CockpitButton></div></section></main><footer className="flex items-center justify-between border-t border-[#2a364b] p-3"><span className="text-xs text-[#8d9ab0]">{dirty ? "Ungespeicherte Änderungen" : "Gespeichert"}</span><CockpitButton tone="primary" onClick={() => void save()} disabled={!dirty || !name.trim() || saving}>{saving ? "Speichert…" : "Änderungen speichern"}</CockpitButton></footer></section></div>
}
