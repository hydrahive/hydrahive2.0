import { useEffect, useState } from "react"
import type { ProjectBrief } from "@/features/chat/api"
import { CockpitButton } from "./CockpitButton"
import { CockpitSectionLabel } from "./CockpitPanel"
import { mediaAssetsApi, type MediaAssetReference } from "./mediaProjectsApi"

export function MediaReferenceOverlay({ projectId, mediaSlug, projects, onClose }: { projectId: string; mediaSlug: string; projects: ProjectBrief[]; onClose: () => void }) {
  const [items, setItems] = useState<MediaAssetReference[]>([])
  const [sourceProject, setSourceProject] = useState(projectId)
  const [label, setLabel] = useState("")
  const [relPath, setRelPath] = useState("")
  const [kind, setKind] = useState<MediaAssetReference["kind"]>("image")
  const [message, setMessage] = useState("Lädt…")
  const reload = () => mediaAssetsApi.list(projectId, mediaSlug).then((data) => { setItems(data); setMessage(`${data.length} Referenzen`) }).catch(() => setMessage("Referenzen nicht erreichbar"))
  useEffect(() => { void reload() }, [projectId, mediaSlug]) // eslint-disable-line react-hooks/exhaustive-deps

  const add = async () => {
    const id = label.toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 64)
    if (!id || !relPath.trim()) { setMessage("Label und relativer Workspace-Pfad fehlen"); return }
    try {
      await mediaAssetsApi.create(projectId, mediaSlug, { id, kind, label: label.trim(), source_project_id: sourceProject, rel_path: relPath.trim() })
      setLabel(""); setRelPath(""); await reload()
    } catch { setMessage("Referenz konnte nicht angelegt werden. Zugriff und Pfad prüfen.") }
  }

  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/80 p-4" role="dialog" aria-modal="true" aria-labelledby="references-title">
    <section className="flex h-[min(760px,92dvh)] w-full max-w-5xl flex-col overflow-hidden rounded-[4px] border border-[#46617f] bg-[#151c2b]">
      <header className="flex items-center justify-between border-b border-[#2a364b] p-4"><div><CockpitSectionLabel>Asset-Zuordnung</CockpitSectionLabel><h2 id="references-title" className="mt-1 text-lg font-semibold text-[#e8eef8]">Persistente Referenzen</h2></div><CockpitButton onClick={onClose}>Schließen</CockpitButton></header>
      <div className="grid gap-3 border-b border-[#2a364b] bg-[#101724] p-4 md:grid-cols-[1fr_150px_1fr_auto]">
        <label className="text-xs text-[#8d9ab0]">Quellprojekt<select value={sourceProject} onChange={(e) => setSourceProject(e.target.value)} className="mt-1 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-2 text-sm text-[#e8eef8]">{projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>
        <label className="text-xs text-[#8d9ab0]">Typ<select value={kind} onChange={(e) => setKind(e.target.value as MediaAssetReference["kind"])} className="mt-1 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-2 text-sm text-[#e8eef8]">{["image", "video", "audio", "voice", "character", "style", "other"].map((value) => <option key={value}>{value}</option>)}</select></label>
        <label className="text-xs text-[#8d9ab0]">Label<input value={label} onChange={(e) => setLabel(e.target.value)} className="mt-1 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-2 text-sm text-[#e8eef8]" /></label>
        <CockpitButton tone="primary" onClick={add} className="self-end">Hinzufügen</CockpitButton>
        <label className="text-xs text-[#8d9ab0] md:col-span-4">Relativer Pfad im Quell-Workspace<input value={relPath} onChange={(e) => setRelPath(e.target.value)} placeholder="atelier/gallery/frame.png" className="mt-1 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-2 font-mono text-sm text-[#e8eef8]" /></label>
      </div>
      <main className="min-h-0 flex-1 overflow-y-auto p-4"><div className="space-y-2">{items.map((item) => <article key={item.id} className="grid gap-3 rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-3 md:grid-cols-[1fr_auto]"><div><strong className="text-sm text-[#e8eef8]">{item.label}</strong><p className="mt-1 break-all font-mono text-xs text-[#8d9ab0]">{item.source_project_id}/{item.rel_path}</p><p className={`mt-1 text-xs ${item.available ? "text-emerald-400" : "text-rose-400"}`}>{item.kind} · {item.mode} · {item.read_only ? "read-only" : "lokale Kopie"} · {item.available ? "verfügbar" : "fehlt"}</p></div><div className="flex items-center gap-2">{item.mode === "reference" && item.available && <CockpitButton onClick={async () => { await mediaAssetsApi.importCopy(projectId, mediaSlug, item.id); await reload() }}>Kopie importieren</CockpitButton>}<CockpitButton onClick={async () => { await mediaAssetsApi.remove(projectId, mediaSlug, item.id); await reload() }}>Entfernen</CockpitButton></div></article>)}</div>{items.length === 0 && <p className="text-center text-sm text-[#8d9ab0]">Noch keine persistenten Asset-Referenzen.</p>}</main>
      <footer className="border-t border-[#2a364b] p-3 text-xs text-[#8d9ab0]">{message} · Referenzen sind read-only; Kopieren ist immer eine bewusste Aktion.</footer>
    </section>
  </div>
}
