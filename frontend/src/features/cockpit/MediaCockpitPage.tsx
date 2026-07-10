import { useEffect, useMemo, useState } from "react"
import { Images, Music2, Palette, Plus, Send, Wand2 } from "lucide-react"
import { chatApi, type ProjectBrief } from "@/features/chat/api"
import { atelierApi } from "@/modules/atelier/api"
import type { AtelierCharacter, AtelierCI, FilmJob, GalleryItem, PresetCatalog, VideoJob } from "@/modules/atelier/types"
import { CockpitButton } from "./CockpitButton"
import { CockpitPanel, CockpitSectionLabel } from "./CockpitPanel"
import { CockpitShell } from "./CockpitShell"
import { CockpitTopbar } from "./CockpitTopbar"
import { openLocalPath } from "./actionRegistry"

const productionAreas = [
  { title: "Idee & Prompt", text: "Grundidee, Ziel, Stil", path: "/atelier" },
  { title: "Drehbuch / Regie", text: "Akte, Szenen, Shots", path: "/atelier" },
  { title: "Charaktere", text: "Personen, Stimmen, Looks", path: "/atelier" },
  { title: "Stil / CI", text: "Look, Kamera, Farben", path: "/atelier" },
]

const pipeline = ["1 Idee", "2 Regie", "3 Assets", "4 Clips", "5 Schnitt"]
const modes = ["Storyboard", "Keyframes", "Clips vorbereiten", "Continue-Frame"]

const fallbackScenes = [
  { title: "Szene 01 — Ankunft", text: "Noch nicht aus Atelier geladen. Als Regie-Slot vorbereitet." },
  { title: "Szene 02 — Dialog", text: "Charaktere, Voiceover und Close-ups planen." },
  { title: "Szene 03 — Finale", text: "Action, Schnitt und Sounddesign sammeln." },
]

export function MediaCockpitPage() {
  const [projects, setProjects] = useState<ProjectBrief[]>([])
  const [projectStatus, setProjectStatus] = useState<"loading" | "ready" | "offline">("loading")
  const [projectId, setProjectId] = useState("")
  const [mediaProject, setMediaProject] = useState("atelier-clips")
  const [atelierStatus, setAtelierStatus] = useState<"idle" | "loading" | "ready" | "offline">("idle")
  const [ci, setCi] = useState<AtelierCI | null>(null)
  const [characters, setCharacters] = useState<AtelierCharacter[]>([])
  const [gallery, setGallery] = useState<GalleryItem[]>([])
  const [videos, setVideos] = useState<VideoJob[]>([])
  const [films, setFilms] = useState<FilmJob[]>([])
  const [presets, setPresets] = useState<PresetCatalog>({})
  const [area, setArea] = useState(productionAreas[0].title)
  const [imageModel, setImageModel] = useState("GPT Image Mini")
  const [videoModel, setVideoModel] = useState("Hailuo 2.3")
  const [audioModel, setAudioModel] = useState("Lyria + TTS default")
  const [jobText, setJobText] = useState("Erzeuge aus Szene 01 ein Storyboard mit 8 Shots. Nutze den Projektstil, Charaktere und Kamera-Presets.")
  const [agentText, setAgentText] = useState("Szene 01 als Storyboard prüfen")

  useEffect(() => {
    chatApi.listProjects()
      .then((items) => {
        setProjects(items)
        setProjectId(items[0]?.id ?? "")
        setProjectStatus("ready")
      })
      .catch(() => setProjectStatus("offline"))
  }, [])

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    setAtelierStatus("loading")
    Promise.allSettled([
      atelierApi.getCI(projectId),
      atelierApi.listCharacters(projectId),
      atelierApi.gallery(projectId),
      atelierApi.listVideos(projectId),
      atelierApi.listFilms(projectId),
      atelierApi.presets(),
    ]).then(([ciResult, charactersResult, galleryResult, videosResult, filmsResult, presetsResult]) => {
      if (cancelled) return
      if (ciResult.status === "fulfilled") { setCi(ciResult.value); setImageModel(ciResult.value.default_model || "GPT Image Mini") }
      if (charactersResult.status === "fulfilled") setCharacters(charactersResult.value)
      if (galleryResult.status === "fulfilled") setGallery(galleryResult.value)
      if (videosResult.status === "fulfilled") setVideos(videosResult.value)
      if (filmsResult.status === "fulfilled") setFilms(filmsResult.value)
      if (presetsResult.status === "fulfilled") setPresets(presetsResult.value)
      setAtelierStatus([ciResult, charactersResult, galleryResult, videosResult, filmsResult, presetsResult].some((result) => result.status === "fulfilled") ? "ready" : "offline")
    })
    return () => { cancelled = true }
  }, [projectId])

  const selectedProject = useMemo(() => projects.find((project) => project.id === projectId), [projects, projectId])
  const activeStep = area.includes("Idee") ? 0 : area.includes("Regie") ? 1 : area.includes("Charakter") || area.includes("Stil") ? 2 : 0
  const mediaAssets = useMemo(() => [
    { kind: "Charakter", name: characters[0]?.name ?? "Atelier-Figuren", count: characters.length, icon: Images, path: "/atelier" },
    { kind: "Stil", name: ci?.style_anchor ? "CI geladen" : "CI / Look", count: ci?.palette?.length ?? 0, icon: Palette, path: "/atelier" },
    { kind: "Bild", name: gallery[0]?.name ?? "Keyframes", count: gallery.length, icon: Wand2, path: "/atelier" },
    { kind: "Clips", name: videos[0]?.status ?? "Videojobs", count: videos.length + films.length, icon: Music2, path: "/videoeditor" },
  ], [characters, ci, gallery, videos, films])

  return (
    <CockpitShell
      eyebrow="Media"
      title="Media-Cockpit"
      description="Produktionsarbeitsplatz für Idee, Regie, Assets, Generator-Aufträge und Schnitt — nach Mockup-Parität, aber ohne automatische Generierungs- oder LLM-Jobs."
      actions={<CockpitButton tone="primary" onClick={() => openLocalPath("/atelier")}>Atelier öffnen</CockpitButton>}
      className="flex h-[100dvh] min-h-0 flex-col overflow-hidden bg-[#080b11]"
      hideHeader
    >
      <CockpitTopbar active="media" context={selectedProject?.name ?? "Projekt: lokal"} action={{ label: "Atelier öffnen", path: "/atelier" }} />
      <div className="grid min-h-0 flex-1 gap-[10px] overflow-hidden p-[10px] xl:grid-cols-[280px_minmax(520px,1fr)_360px]">
        <aside className="panel min-h-0 overflow-y-auto rounded-[4px] border border-[#2a364b] bg-[#151c2b] p-3">
          <CockpitSectionLabel>Media-Projekt</CockpitSectionLabel>
          <select value={mediaProject} onChange={(event) => setMediaProject(event.target.value)} className="mt-2 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]">
            <option value="testfilm">Filmprojekt: Testfilm 90min</option>
            <option value="atelier-clips">Atelier Clips</option>
            <option value="buddy-trailer">Buddy Trailer</option>
          </select>

          <div className="mt-4">
            <CockpitSectionLabel>Projektbindung</CockpitSectionLabel>
            <select value={projectId} onChange={(event) => setProjectId(event.target.value)} className="mt-2 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]">
              {projectStatus === "offline" && <option>Projektliste offline</option>}
              {projects.length === 0 && projectStatus !== "offline" && <option>Lokale Projekte laden…</option>}
              {projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
            </select>
            <p className="mt-2 text-xs leading-4 text-[#8d9ab0]">Assets liegen im Projekt/Workspace und bleiben zurückverlinkt. Projekte: {projectStatus === "ready" ? "lokal geladen" : projectStatus === "offline" ? "offline nutzbar" : "lädt"}. Atelier: {atelierStatus === "ready" ? `${characters.length} Figuren · ${gallery.length} Bilder · ${videos.length} Clips` : atelierStatus === "loading" ? "lädt" : "offline/leer"}.</p>
          </div>

          <div className="mt-4">
            <CockpitSectionLabel>Produktionsbereich</CockpitSectionLabel>
            <div className="mt-2 space-y-2">
              {productionAreas.map((item) => (
                <button key={item.title} onClick={() => setArea(item.title)} className={["w-full rounded-[4px] border p-2 text-left transition-colors", area === item.title ? "border-[#ffb86b]/55 bg-[#30243a]" : "border-[#2a364b] bg-[#111827] hover:border-[#46617f]"].join(" ")}>
                  <strong className="block text-sm text-[#e8eef8]">{item.title}</strong>
                  <span className="text-xs text-[#8d9ab0]">{item.text}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="mt-4">
            <CockpitSectionLabel>Modelle</CockpitSectionLabel>
            <label className="mt-2 block text-xs text-[#8d9ab0]">Bild</label>
            <select value={imageModel} onChange={(event) => setImageModel(event.target.value)} className="w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]"><option>GPT Image Mini</option><option>Gemini Flash Image</option></select>
            <label className="mt-2 block text-xs text-[#8d9ab0]">Video</label>
            <select value={videoModel} onChange={(event) => setVideoModel(event.target.value)} className="w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]"><option>Hailuo 2.3</option><option>Kling 3.0</option><option>Seedance 2.0</option><option>Veo 3.1</option></select>
            <label className="mt-2 block text-xs text-[#8d9ab0]">Musik/Voice</label>
            <select value={audioModel} onChange={(event) => setAudioModel(event.target.value)} className="w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]"><option>Lyria + TTS default</option><option>Nur Musik</option><option>Nur Voice</option></select>
            <p className="mt-3 text-xs leading-4 text-[#8d9ab0]">CI: {ci?.style_anchor ? ci.style_anchor.slice(0, 90) : "noch kein Stil geladen"}{ci?.style_anchor && ci.style_anchor.length > 90 ? "…" : ""}</p>
            <p className="mt-1 text-xs text-[#8d9ab0]">Presets: {Object.keys(presets).length || 0} Gruppen</p>
          </div>
        </aside>

        <main className="panel grid min-h-0 grid-rows-[auto_1fr_auto] overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#151c2b]">
          <div className="grid grid-cols-5 gap-2 border-b border-[#2a364b] bg-[#111827] p-3">
            {pipeline.map((step, index) => <div key={step} className={["rounded-[4px] border p-2 text-center text-xs", index <= activeStep ? "border-[#ffb86b]/55 bg-[#ffb86b]/10 text-[#ffb86b]" : "border-[#2a364b] bg-[#0d1420] text-[#8d9ab0]"].join(" ")}>{step}</div>)}
          </div>

          <section className="grid min-h-0 gap-[10px] overflow-y-auto p-3 md:grid-cols-2">
            <div className="rounded-[4px] border border-[#2a364b] bg-[#111827] p-3">
              <div className="mb-3 flex items-center justify-between gap-2">
                <CockpitSectionLabel>Drehbuch / Szenen</CockpitSectionLabel>
                <CockpitButton onClick={() => openLocalPath("/atelier")}><Plus size={12} className="mr-1 inline" /> Szene +</CockpitButton>
              </div>
              <div className="space-y-2">
                {fallbackScenes.map((scene, index) => (
                  <button key={scene.title} onClick={() => setJobText(`Erzeuge aus ${scene.title} ein Storyboard mit 8 Shots. Nutze den Projektstil, Charaktere und Kamera-Presets.`)} className="grid w-full grid-cols-[82px_1fr] gap-3 rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-2 text-left hover:border-[#46617f]">
                    <div className="h-[54px] rounded-[4px] border border-[#2a364b] bg-[linear-gradient(135deg,#3b2342,#7c3a1b)]" />
                    <div><strong className="block text-sm text-[#e8eef8]">{scene.title}</strong><p className="mt-1 text-xs leading-4 text-[#8d9ab0]">{scene.text}</p><span className="mt-1 block font-mono text-[10px] text-[#69d7ff]">Slot {index + 1}</span></div>
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-[4px] border border-[#2a364b] bg-[#111827] p-3">
              <div className="mb-3 flex items-center justify-between gap-2">
                <CockpitSectionLabel>Generator-Auftrag</CockpitSectionLabel>
                <CockpitButton onClick={() => openLocalPath("/atelier")}>Overlay öffnen</CockpitButton>
              </div>
              <textarea value={jobText} onChange={(event) => setJobText(event.target.value)} rows={8} className="w-full resize-y rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm leading-5 text-[#e8eef8]" />
              <div className="mt-3 flex flex-wrap gap-2">{modes.map((mode) => <button key={mode} onClick={() => setJobText((text) => `${text}\n# ${mode}`)} className="rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2 py-1 text-xs text-[#d7deea] hover:border-[#46617f]">{mode}</button>)}</div>
              <p className="mt-3 text-xs leading-4 text-[#8d9ab0]">Offline-first: Dieser Auftrag wird hier nur vorbereitet. Generierung startet erst bewusst im Atelier/Overlay.</p>
            </div>
          </section>

          <section className="border-t border-[#2a364b] bg-[#101724] p-3">
            <div className="mb-2 flex items-center justify-between gap-2"><CockpitSectionLabel>Schnitt-Timeline</CockpitSectionLabel><CockpitButton tone="primary" onClick={() => openLocalPath("/videoeditor")}>Export / Schnitt</CockpitButton></div>
            <div className="space-y-2">
              <TimelineTrack label="Video" clips={[{ left: 3, width: 22 }, { left: 30, width: 18 }, { left: 55, width: 32 }]} />
              <TimelineTrack label="Voice" clips={[{ left: 30, width: 18, color: "#69d7ff" }]} />
              <TimelineTrack label="Musik" clips={[{ left: 0, width: 88, color: "#4ade80" }]} />
            </div>
          </section>
        </main>

        <aside className="grid min-h-0 grid-rows-[42%_58%] gap-[10px] overflow-hidden">
          <CockpitPanel title="Asset-Bibliothek" eyebrow="Material" actions={<CockpitButton onClick={() => openLocalPath("/atelier")}>Import</CockpitButton>} className="min-h-0 overflow-y-auto">
            <div className="grid grid-cols-2 gap-2">
              {mediaAssets.map((asset) => {
                const Icon = asset.icon
                return <button key={asset.kind} onClick={() => openLocalPath(asset.path)} className="h-[76px] rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-2 text-left text-xs text-[#8d9ab0] hover:border-[#46617f]"><Icon size={14} className="mb-1 text-[#ffb86b]" />{asset.kind} · {asset.count}<strong className="block truncate text-sm text-[#e8eef8]">{asset.name}</strong></button>
              })}
            </div>
          </CockpitPanel>

          <section className="panel flex min-h-0 flex-col overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#151c2b]">
            <div className="flex items-start justify-between gap-3 border-b border-[#2a364b] p-3"><div><CockpitSectionLabel>Media-Agent</CockpitSectionLabel><p className="mt-1 text-xs text-[#8d9ab0]">Regie, Generierung, Schnitt</p></div><CockpitButton onClick={() => openLocalPath("/buddy")}>Session</CockpitButton></div>
            <div className="flex-1 space-y-2 overflow-y-auto p-3">
              <div className="rounded-[4px] border border-[#2a364b] bg-[#1b2536] p-2 text-sm leading-5 text-[#d7deea]">Ich kann aus deiner Szene Shots bauen und danach Keyframes vorbereiten.</div>
              <div className="rounded-[4px] border border-[#2a364b] bg-[#1b2536] p-2 text-sm leading-5 text-[#d7deea]">Nächster sinnvoller Schritt: Szene 01 als Storyboard prüfen.</div>
            </div>
            <div className="flex gap-2 border-t border-[#2a364b] p-2"><input value={agentText} onChange={(event) => setAgentText(event.target.value)} placeholder="Media-Auftrag…" className="min-w-0 flex-1 rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]" /><CockpitButton tone="primary" onClick={() => openLocalPath("/buddy")}><Send size={12} /></CockpitButton></div>
          </section>
        </aside>
      </div>
    </CockpitShell>
  )
}

function TimelineTrack({ label, clips }: { label: string; clips: Array<{ left: number; width: number; color?: string }> }) {
  return <div className="grid grid-cols-[70px_1fr] items-center gap-2"><span className="text-xs text-[#8d9ab0]">{label}</span><div className="relative h-5 rounded-[2px] border border-[#2a364b] bg-[#0d1420]">{clips.map((clip, index) => <div key={index} className="absolute top-0 h-full rounded-[2px] bg-[linear-gradient(90deg,#ffb86b,#c084fc)]" style={{ left: `${clip.left}%`, width: `${clip.width}%`, background: clip.color }} />)}</div></div>
}
