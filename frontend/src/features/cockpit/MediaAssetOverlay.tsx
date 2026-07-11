import { useMemo, useState } from "react"
import { fileUrl } from "@/modules/atelier/api"
import type { AtelierCharacter, AtelierCI, FilmJob, GalleryItem, VideoJob } from "@/modules/atelier/types"
import { CockpitButton } from "./CockpitButton"
import { CockpitSectionLabel } from "./CockpitPanel"
import { openLocalPath } from "./actionRegistry"

type AssetTab = "all" | "characters" | "style" | "images" | "video" | "audio"

export function MediaAssetOverlay({ tab: initialTab, root, ci, characters, gallery, videos, films, onClose }: { tab: AssetTab; root: string; ci: AtelierCI | null; characters: AtelierCharacter[]; gallery: GalleryItem[]; videos: VideoJob[]; films: FilmJob[]; onClose: () => void }) {
  const [tab, setTab] = useState<AssetTab>(initialTab)
  const items = useMemo(() => {
    if (tab === "characters") return characters.map((item) => ({ id: item.id, title: item.name, detail: item.description || item.style_anchor || "Kein Steckbrief", image: item.references[0] ? fileUrl(`${root}/${item.references[0]}`) : "" }))
    if (tab === "images") return gallery.map((item) => ({ id: item.rel, title: item.name, detail: item.prompt || item.model || "Galeriebild", image: fileUrl(item.path) }))
    if (tab === "video") return [...videos.map((item) => ({ id: item.job_id, title: `Clip · ${item.status}`, detail: item.prompt || item.source_rel, image: "" })), ...films.map((item) => ({ id: item.job_id, title: `Film · ${item.status}`, detail: `${item.clips.length} Clips · ${item.resolution}`, image: "" }))]
    return []
  }, [tab, characters, gallery, videos, films, root])

  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/80 p-4" role="dialog" aria-modal="true" aria-labelledby="asset-overlay-title">
    <section className="flex h-[min(780px,92dvh)] w-full max-w-6xl flex-col overflow-hidden rounded-[4px] border border-[#46617f] bg-[#151c2b] shadow-2xl">
      <header className="flex items-center justify-between border-b border-[#2a364b] p-4"><div><CockpitSectionLabel>Media-Workspace</CockpitSectionLabel><h2 id="asset-overlay-title" className="mt-1 text-lg font-semibold text-[#e8eef8]">Asset-Bibliothek</h2></div><CockpitButton onClick={onClose}>Schließen</CockpitButton></header>
      <nav className="flex flex-wrap gap-2 border-b border-[#2a364b] bg-[#101724] p-3">{(["all", "characters", "style", "images", "video", "audio"] as AssetTab[]).map((key) => <button key={key} onClick={() => setTab(key)} className={`rounded-[4px] border px-3 py-1.5 text-xs ${tab === key ? "border-[#ffb86b]/60 bg-[#ffb86b]/10 text-[#ffb86b]" : "border-[#2a364b] text-[#8d9ab0]"}`}>{labels[key]}</button>)}</nav>
      <main className="min-h-0 flex-1 overflow-y-auto p-4">
        {tab === "all" && <div className="grid gap-3 md:grid-cols-3">{summaryCard("Charaktere", characters.length, "characters", setTab)}{summaryCard("Bilder / Keyframes", gallery.length, "images", setTab)}{summaryCard("Clips / Filme", videos.length + films.length, "video", setTab)}{summaryCard("Stil / CI", ci?.style_anchor ? 1 : 0, "style", setTab)}{summaryCard("Musik / Voice", 0, "audio", setTab)}</div>}
        {tab === "style" && <div className="rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-4"><h3 className="font-semibold text-[#e8eef8]">Projektstil</h3><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[#d7deea]">{ci?.style_anchor || "Noch kein Style-Anchor hinterlegt."}</p><div className="mt-4 flex flex-wrap gap-2">{ci?.palette.map((color) => <span key={color} className="h-9 w-16 rounded-[3px] border border-white/20" style={{ background: color }} title={color} />)}</div><p className="mt-4 text-xs text-[#8d9ab0]">Modell: {ci?.default_model || "nicht gesetzt"} · Format: {ci?.aspect_ratio || "nicht gesetzt"}</p><CockpitButton onClick={() => openLocalPath("/atelier")} className="mt-4">CI im Atelier bearbeiten</CockpitButton></div>}
        {tab === "audio" && <div className="rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-5"><h3 className="font-semibold text-[#e8eef8]">Musik und Voice</h3><p className="mt-2 text-sm leading-6 text-[#8d9ab0]">Audio-Assets werden über die Musik- und Voice-Werkzeuge erstellt und anschließend dem Media-Projekt referenziert. Diese Ansicht startet keinen Job.</p><div className="mt-4 flex gap-2"><CockpitButton onClick={() => openLocalPath("/music")}>Musik öffnen</CockpitButton><CockpitButton onClick={() => openLocalPath("/atelier")}>Voice / Regie öffnen</CockpitButton></div></div>}
        {items.length > 0 && <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{items.map((item) => <article key={item.id} className="overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#0d1420]">{item.image ? <img src={item.image} alt="" className="h-40 w-full object-cover" loading="lazy" /> : <div className="grid h-28 place-items-center bg-[#111827] text-xs text-[#46617f]">Keine lokale Vorschau</div>}<div className="p-3"><h3 className="truncate text-sm font-semibold text-[#e8eef8]">{item.title}</h3><p className="mt-1 line-clamp-3 text-xs leading-5 text-[#8d9ab0]">{item.detail}</p></div></article>)}</div>}
        {tab !== "all" && tab !== "style" && tab !== "audio" && items.length === 0 && <p className="rounded-[4px] border border-dashed border-[#2a364b] p-6 text-center text-sm text-[#8d9ab0]">Noch keine Assets in diesem Bereich. Öffne das Atelier, um Material anzulegen.</p>}
      </main>
    </section>
  </div>
}

const labels: Record<AssetTab, string> = { all: "Übersicht", characters: "Charaktere", style: "Stil / CI", images: "Bilder", video: "Video", audio: "Musik / Voice" }
function summaryCard(title: string, count: number, tab: AssetTab, select: (tab: AssetTab) => void) { return <button onClick={() => select(tab)} className="rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-4 text-left hover:border-[#46617f]"><strong className="text-[#e8eef8]">{title}</strong><span className="mt-2 block font-mono text-2xl text-[#ffb86b]">{count}</span></button> }
