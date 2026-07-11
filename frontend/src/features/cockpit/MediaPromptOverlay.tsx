import { useEffect, useMemo, useState } from "react"
import { CockpitButton } from "./CockpitButton"
import { CockpitSectionLabel } from "./CockpitPanel"
import { mediaPromptsApi, type MediaPrompt, type MediaPromptType } from "./mediaProjectsApi"

const types: Array<{ value: MediaPromptType; label: string }> = [
  { value: "general", label: "Allgemein" }, { value: "storyboard", label: "Storyboard" },
  { value: "image", label: "Bild" }, { value: "video", label: "Video" },
  { value: "music", label: "Musik" }, { value: "voice", label: "Voice" },
]

export function MediaPromptOverlay({ projectId, mediaSlug, initialBody, onClose }: { projectId: string; mediaSlug: string; initialBody: string; onClose: () => void }) {
  const [items, setItems] = useState<MediaPrompt[]>([])
  const [selected, setSelected] = useState("")
  const [type, setType] = useState<MediaPromptType>("storyboard")
  const [title, setTitle] = useState("Neuer Prompt")
  const [model, setModel] = useState("")
  const [body, setBody] = useState(initialBody)
  const [status, setStatus] = useState("Lädt…")
  const active = useMemo(() => items.find((item) => `${item.type}/${item.slug}` === selected), [items, selected])

  const reload = () => mediaPromptsApi.list(projectId, mediaSlug).then((data) => { setItems(data); setStatus(data.length ? "Archiv geladen" : "Noch keine Einträge") }).catch(() => setStatus("Archiv nicht erreichbar"))
  useEffect(() => { void reload() }, [projectId, mediaSlug]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!active) return; setType(active.type); setTitle(active.title); setModel(active.model); setBody(active.body) }, [active])

  const save = async () => {
    if (!title.trim()) { setStatus("Titel fehlt"); return }
    setStatus("Speichert…")
    try {
      if (active) await mediaPromptsApi.update(projectId, mediaSlug, active.type, active.slug, { title: title.trim(), body, model })
      else {
        const slug = title.toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 64)
        if (!slug) { setStatus("Ungültiger Titel"); return }
        await mediaPromptsApi.create(projectId, mediaSlug, { slug, type, title: title.trim(), body, model, asset_refs: [] })
        setSelected(`${type}/${slug}`)
      }
      await reload(); setStatus("Draft gespeichert — kein Job gestartet")
    } catch { setStatus("Speichern fehlgeschlagen oder Slug bereits vorhanden") }
  }

  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/80 p-4" role="dialog" aria-modal="true" aria-labelledby="prompt-overlay-title">
    <section className="grid h-[min(760px,92dvh)] w-full max-w-5xl grid-cols-[260px_1fr] overflow-hidden rounded-[4px] border border-[#46617f] bg-[#151c2b] shadow-2xl">
      <aside className="overflow-y-auto border-r border-[#2a364b] bg-[#101724] p-3">
        <CockpitSectionLabel>Promptarchiv</CockpitSectionLabel>
        <button onClick={() => { setSelected(""); setTitle("Neuer Prompt"); setBody(initialBody); setModel("") }} className="mt-3 w-full rounded-[4px] border border-[#ffb86b]/55 bg-[#ffb86b]/10 p-2 text-left text-sm text-[#ffb86b]">+ Neuer Draft</button>
        <div className="mt-3 space-y-2">{items.map((item) => <button key={`${item.type}/${item.slug}`} onClick={() => setSelected(`${item.type}/${item.slug}`)} className="w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-2 text-left hover:border-[#46617f]"><strong className="block truncate text-sm text-[#e8eef8]">{item.title}</strong><span className="text-[11px] text-[#8d9ab0]">{item.type} · {item.status}</span></button>)}</div>
      </aside>
      <main className="flex min-h-0 flex-col">
        <header className="flex items-center justify-between border-b border-[#2a364b] p-4"><div><CockpitSectionLabel>Offline-Workspace</CockpitSectionLabel><h2 id="prompt-overlay-title" className="mt-1 text-lg font-semibold text-[#e8eef8]">Prompt bearbeiten</h2></div><CockpitButton onClick={onClose}>Schließen</CockpitButton></header>
        <div className="grid flex-1 content-start gap-3 overflow-y-auto p-4 md:grid-cols-2">
          <label className="text-xs text-[#8d9ab0]">Typ<select disabled={!!active} value={type} onChange={(event) => setType(event.target.value as MediaPromptType)} className="mt-1 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]">{types.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          <label className="text-xs text-[#8d9ab0]">Modell<input value={model} onChange={(event) => setModel(event.target.value)} className="mt-1 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]" /></label>
          <label className="text-xs text-[#8d9ab0] md:col-span-2">Titel<input value={title} onChange={(event) => setTitle(event.target.value)} className="mt-1 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]" /></label>
          <label className="text-xs text-[#8d9ab0] md:col-span-2">Prompt<textarea value={body} onChange={(event) => setBody(event.target.value)} rows={18} className="mt-1 w-full resize-y rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 font-mono text-sm leading-5 text-[#e8eef8]" /></label>
        </div>
        <footer className="flex items-center justify-between gap-3 border-t border-[#2a364b] p-3"><p className="text-xs text-[#8d9ab0]">{status}</p><CockpitButton tone="primary" onClick={save}>Draft speichern</CockpitButton></footer>
      </main>
    </section>
  </div>
}
