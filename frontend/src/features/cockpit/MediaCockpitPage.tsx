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
import { mediaProjectsApi, type MediaProject } from "./mediaProjectsApi"
import { MediaPromptOverlay } from "./MediaPromptOverlay"
import { MediaAssetOverlay } from "./MediaAssetOverlay"
import { MediaReferenceOverlay } from "./MediaReferenceOverlay"
import { MediaScreenplayOverlay } from "./MediaScreenplayOverlay"
import { MediaAgentPopup } from "./MediaAgentPopup"
import { MediaTimelineOverlay } from "./MediaTimelineOverlay"
import { MediaIdeaOverlay } from "./media/MediaIdeaOverlay"
import { mediaWorkspaceAreas, type MediaWorkspaceArea } from "./media/mediaWorkspaceNavigation"

const pipeline = ["1 Idee", "2 Regie", "3 Assets", "4 Clips", "5 Schnitt"]
const modes = ["Storyboard", "Keyframes", "Clips vorbereiten", "Continue-Frame"]

const fallbackScenes = [
  { title: "Szene 01 — Ankunft", text: "Noch nicht aus Atelier geladen. Als Regie-Slot vorbereitet.", source: "Entwurf" },
  { title: "Szene 02 — Dialog", text: "Charaktere, Voiceover und Close-ups planen.", source: "Entwurf" },
  { title: "Szene 03 — Finale", text: "Action, Schnitt und Sounddesign sammeln.", source: "Entwurf" },
]

export function MediaCockpitPage() {
  const [projects, setProjects] = useState<ProjectBrief[]>([])
  const [projectStatus, setProjectStatus] = useState<"loading" | "ready" | "offline">("loading")
  const [projectId, setProjectId] = useState("")
  const [mediaProjects, setMediaProjects] = useState<MediaProject[]>([])
  const [mediaProject, setMediaProject] = useState("")
  const [mediaProjectStatus, setMediaProjectStatus] = useState<"idle" | "loading" | "ready" | "offline">("idle")
  const [createOpen, setCreateOpen] = useState(false)
  const [ideaOpen, setIdeaOpen] = useState(false)
  const [promptOpen, setPromptOpen] = useState(false)
  const [assetTab, setAssetTab] = useState<"all" | "characters" | "style" | "images" | "video" | "audio" | null>(null)
  const [atelierRoot, setAtelierRoot] = useState("")
  const [referencesOpen, setReferencesOpen] = useState(false)
  const [screenplayOpen, setScreenplayOpen] = useState(false)
  const [timelineOpen, setTimelineOpen] = useState(false)
  const [createName, setCreateName] = useState("")
  const [createDescription, setCreateDescription] = useState("")
  const [createError, setCreateError] = useState("")
  const [atelierStatus, setAtelierStatus] = useState<"idle" | "loading" | "ready" | "offline">("idle")
  const [ci, setCi] = useState<AtelierCI | null>(null)
  const [characters, setCharacters] = useState<AtelierCharacter[]>([])
  const [gallery, setGallery] = useState<GalleryItem[]>([])
  const [videos, setVideos] = useState<VideoJob[]>([])
  const [films, setFilms] = useState<FilmJob[]>([])
  const [presets, setPresets] = useState<PresetCatalog>({})
  const [area, setArea] = useState<MediaWorkspaceArea>("idea")
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
    setMediaProjectStatus("loading")
    mediaProjectsApi.list(projectId).then((items) => {
      if (cancelled) return
      setMediaProjects(items)
      setMediaProject((current) => items.some((item) => item.slug === current) ? current : (items[0]?.slug ?? ""))
      setMediaProjectStatus("ready")
    }).catch(() => {
      if (!cancelled) setMediaProjectStatus("offline")
    })
    return () => { cancelled = true }
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    setAtelierStatus("loading")
    Promise.allSettled([
      atelierApi.meta(projectId),
      atelierApi.getCI(projectId),
      atelierApi.listCharacters(projectId),
      atelierApi.gallery(projectId),
      atelierApi.listVideos(projectId),
      atelierApi.listFilms(projectId),
      atelierApi.presets(),
    ]).then(([metaResult, ciResult, charactersResult, galleryResult, videosResult, filmsResult, presetsResult]) => {
      if (cancelled) return
      if (metaResult.status === "fulfilled") setAtelierRoot(metaResult.value.root)
      if (ciResult.status === "fulfilled") { setCi(ciResult.value); setImageModel(ciResult.value.default_model || "GPT Image Mini") }
      if (charactersResult.status === "fulfilled") setCharacters(charactersResult.value)
      if (galleryResult.status === "fulfilled") setGallery(galleryResult.value)
      if (videosResult.status === "fulfilled") setVideos(videosResult.value)
      if (filmsResult.status === "fulfilled") setFilms(filmsResult.value)
      if (presetsResult.status === "fulfilled") setPresets(presetsResult.value)
      setAtelierStatus([metaResult, ciResult, charactersResult, galleryResult, videosResult, filmsResult, presetsResult].some((result) => result.status === "fulfilled") ? "ready" : "offline")
    })
    return () => { cancelled = true }
  }, [projectId])

  const selectedProject = useMemo(() => projects.find((project) => project.id === projectId), [projects, projectId])
  const selectedMediaProject = useMemo(() => mediaProjects.find((project) => project.slug === mediaProject), [mediaProjects, mediaProject])
  const activeStep = mediaWorkspaceAreas.find((item) => item.id === area)?.step ?? 0
  const mediaAssets = useMemo(() => [
    { kind: "Charakter", name: characters[0]?.name ?? "Atelier-Figuren", count: characters.length, icon: Images, tab: "characters" as const },
    { kind: "Stil", name: ci?.style_anchor ? "CI geladen" : "CI / Look", count: ci?.palette?.length ?? 0, icon: Palette, tab: "style" as const },
    { kind: "Bild", name: gallery[0]?.name ?? "Keyframes", count: gallery.length, icon: Wand2, tab: "images" as const },
    { kind: "Clips", name: videos[0]?.status ?? "Videojobs", count: videos.length + films.length, icon: Music2, tab: "video" as const },
  ], [characters, ci, gallery, videos, films])
  const productionSlots = useMemo(() => {
    const imageSlots = gallery.slice(0, 3).map((item, index) => ({
      title: `Keyframe ${String(index + 1).padStart(2, "0")} — ${item.name}`,
      text: item.prompt ?? `Bild aus Galerie: ${item.rel}`,
      source: "Galerie",
    }))
    const videoSlots = videos.slice(0, 3 - imageSlots.length).map((item, index) => ({
      title: `Clip ${String(index + 1).padStart(2, "0")} — ${item.status}`,
      text: item.prompt || item.source_rel,
      source: "Videojob",
    }))
    return [...imageSlots, ...videoSlots, ...fallbackScenes].slice(0, 3)
  }, [gallery, videos])
  const timelineVideoClips = useMemo(() => videos.length > 0 ? videos.slice(0, 5).map((job, index) => ({ left: index * 18, width: 14, color: statusColor(job.status) })) : [{ left: 3, width: 22 }, { left: 30, width: 18 }, { left: 55, width: 32 }], [videos])
  const timelineFilmClips = useMemo(() => films.length > 0 ? films.slice(0, 3).map((job, index) => ({ left: index * 28, width: 22, color: statusColor(job.status) })) : [{ left: 30, width: 18, color: "#69d7ff" }], [films])
  const modePills = useMemo(() => {
    const presetNames = Object.values(presets).flat().slice(0, 4)
    return presetNames.length ? presetNames : modes
  }, [presets])

  function openArea(next: MediaWorkspaceArea) {
    setArea(next)
    if (next === "idea") setIdeaOpen(true)
    if (next === "prompts") setPromptOpen(true)
    if (next === "screenplay") setScreenplayOpen(true)
    if (next === "characters") setAssetTab("characters")
    if (next === "style") setAssetTab("style")
    if (next === "assets") setAssetTab("all")
    if (next === "timeline") setTimelineOpen(true)
  }

  async function saveIdea(input: { name: string; description: string }) {
    if (!projectId || !mediaProject) return
    const updated = await mediaProjectsApi.update(projectId, mediaProject, input)
    setMediaProjects((items) => items.map((item) => item.slug === updated.slug ? updated : item))
  }

  const createMediaProject = async () => {
    const name = createName.trim()
    const slug = name.toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 64)
    if (!projectId || !name || !slug) { setCreateError("Bitte einen gültigen Namen eingeben."); return }
    setCreateError("")
    try {
      const created = await mediaProjectsApi.create(projectId, { slug, name, description: createDescription.trim() })
      setMediaProjects((items) => [...items, created])
      setMediaProject(created.slug)
      setCreateOpen(false)
      setCreateName("")
      setCreateDescription("")
    } catch { setCreateError("Media-Projekt konnte nicht angelegt werden.") }
  }

  return (
    <CockpitShell
      eyebrow="Media"
      title="Media-Cockpit"
      description="Produktionsarbeitsplatz für Idee, Regie, Assets, Generator-Aufträge und Schnitt — nach Mockup-Parität, aber ohne automatische Generierungs- oder LLM-Jobs."
      actions={<CockpitButton tone="primary" onClick={() => openLocalPath("/atelier")}>Atelier öffnen</CockpitButton>}
      className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]"
      hideHeader
    >
      <CockpitTopbar active="media" context={selectedProject?.name ?? "Projekt: lokal"} action={{ label: "Atelier öffnen", path: "/atelier" }} />
      <div className="grid min-h-0 flex-1 gap-[10px] overflow-hidden p-[10px] xl:grid-cols-[280px_minmax(520px,1fr)_360px]">
        <aside className="panel min-h-0 overflow-y-auto rounded-[4px] border border-[#2a364b] bg-[#151c2b] p-3">
          <div className="flex items-center justify-between gap-2"><CockpitSectionLabel>Media-Projekt</CockpitSectionLabel><CockpitButton onClick={() => setCreateOpen(true)}><Plus size={12} className="mr-1 inline" /> Neu</CockpitButton></div>
          <select value={mediaProject} onChange={(event) => setMediaProject(event.target.value)} disabled={!mediaProjects.length} className="mt-2 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8] disabled:opacity-60">
            {!mediaProjects.length && <option value="">{mediaProjectStatus === "loading" ? "Media-Projekte laden…" : mediaProjectStatus === "offline" ? "Media-Projekte offline" : "Noch kein Media-Projekt"}</option>}
            {mediaProjects.map((item) => <option key={item.slug} value={item.slug}>{item.name}</option>)}
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
              {mediaWorkspaceAreas.map((item) => (
                <button key={item.id} disabled={!mediaProject} onClick={() => openArea(item.id)} className={["w-full rounded-[4px] border p-2 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50", area === item.id ? "border-[#ffb86b]/55 bg-[#30243a]" : "border-[#2a364b] bg-[#111827] hover:border-[#46617f]"].join(" ")}>
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
                <CockpitButton onClick={() => setScreenplayOpen(true)} disabled={!mediaProject}><Plus size={12} className="mr-1 inline" /> Regie öffnen</CockpitButton>
              </div>
              <div className="space-y-2">
                {productionSlots.map((scene, index) => (
                  <button key={scene.title} onClick={() => setJobText(`Erzeuge aus ${scene.title} ein Storyboard mit 8 Shots. Nutze den Projektstil, Charaktere und Kamera-Presets.\n\nQuelle: ${scene.text}`)} className="grid w-full grid-cols-[82px_1fr] gap-3 rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-2 text-left hover:border-[#46617f]">
                    <div className="h-[54px] rounded-[4px] border border-[#2a364b] bg-[linear-gradient(135deg,#3b2342,#7c3a1b)]" />
                    <div><strong className="block text-sm text-[#e8eef8]">{scene.title}</strong><p className="mt-1 max-h-8 overflow-hidden text-xs leading-4 text-[#8d9ab0]">{scene.text}</p><span className="mt-1 block font-mono text-[10px] text-[#69d7ff]">{scene.source} · Slot {index + 1}</span></div>
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-[4px] border border-[#2a364b] bg-[#111827] p-3">
              <div className="mb-3 flex items-center justify-between gap-2">
                <CockpitSectionLabel>Generator-Auftrag</CockpitSectionLabel>
                <CockpitButton onClick={() => setPromptOpen(true)} disabled={!projectId || !mediaProject}>Promptarchiv</CockpitButton>
              </div>
              <textarea value={jobText} onChange={(event) => setJobText(event.target.value)} rows={8} className="w-full resize-y rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm leading-5 text-[#e8eef8]" />
              <div className="mt-3 flex flex-wrap gap-2">{modePills.map((mode) => <button key={mode} onClick={() => setJobText((text) => `${text}\n# ${mode}`)} className="rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2 py-1 text-xs text-[#d7deea] hover:border-[#46617f]">{mode}</button>)}</div>
              <p className="mt-3 text-xs leading-4 text-[#8d9ab0]">Offline-first: Dieser Auftrag wird hier nur vorbereitet. Generierung startet erst bewusst im Atelier/Overlay.</p>
            </div>
          </section>

          <section className="border-t border-[#2a364b] bg-[#101724] p-3">
            <div className="mb-2 flex items-center justify-between gap-2"><CockpitSectionLabel>Schnitt-Timeline</CockpitSectionLabel><CockpitButton tone="primary" onClick={() => setTimelineOpen(true)} disabled={!mediaProject}>Schnitt öffnen</CockpitButton></div>
            <div className="space-y-2">
              <TimelineTrack label="Video" clips={timelineVideoClips} />
              <TimelineTrack label="Film" clips={timelineFilmClips} />
              <TimelineTrack label="Assets" clips={[{ left: 0, width: Math.min(88, Math.max(12, gallery.length * 8)), color: gallery.length ? "#4ade80" : "#2a364b" }]} />
            </div>
          </section>
        </main>

        <aside className="grid min-h-0 grid-rows-[42%_58%] gap-[10px] overflow-hidden">
          <CockpitPanel title="Asset-Bibliothek" eyebrow="Material" actions={<><CockpitButton onClick={() => setReferencesOpen(true)} disabled={!mediaProject}>Referenzen</CockpitButton><CockpitButton onClick={() => setAssetTab("all")}>Öffnen</CockpitButton></>} className="min-h-0 overflow-y-auto">
            <div className="grid grid-cols-2 gap-2">
              {mediaAssets.map((asset) => {
                const Icon = asset.icon
                return <button key={asset.kind} onClick={() => setAssetTab(asset.tab)} className="h-[76px] rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-2 text-left text-xs text-[#8d9ab0] hover:border-[#46617f]"><Icon size={14} className="mb-1 text-[#ffb86b]" />{asset.kind} · {asset.count}<strong className="block truncate text-sm text-[#e8eef8]">{asset.name}</strong></button>
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
      {ideaOpen && selectedMediaProject && <MediaIdeaOverlay project={selectedMediaProject} onSave={saveIdea} onClose={() => setIdeaOpen(false)} />}
      {promptOpen && projectId && mediaProject && <MediaPromptOverlay projectId={projectId} mediaSlug={mediaProject} initialBody={jobText} onClose={() => setPromptOpen(false)} />}
      {assetTab && <MediaAssetOverlay tab={assetTab} root={atelierRoot} ci={ci} characters={characters} gallery={gallery} videos={videos} films={films} onClose={() => setAssetTab(null)} />}
      {referencesOpen && projectId && mediaProject && <MediaReferenceOverlay projectId={projectId} mediaSlug={mediaProject} projects={projects} onClose={() => setReferencesOpen(false)} />}
      {screenplayOpen && projectId && mediaProject && <MediaScreenplayOverlay projectId={projectId} mediaSlug={mediaProject} onClose={() => setScreenplayOpen(false)} />}
      {timelineOpen && projectId && mediaProject && <MediaTimelineOverlay projectId={projectId} mediaSlug={mediaProject} onClose={() => setTimelineOpen(false)} />}
      {projectId && mediaProject && <MediaAgentPopup projectId={projectId} mediaSlug={mediaProject} promptDraft={jobText} />}
      {createOpen && <div className="fixed inset-0 z-50 grid place-items-center bg-black/75 p-4" role="dialog" aria-modal="true" aria-labelledby="create-media-title">
        <section className="w-full max-w-lg rounded-[4px] border border-[#46617f] bg-[#151c2b] shadow-2xl">
          <header className="border-b border-[#2a364b] p-4"><CockpitSectionLabel>Neues Media-Projekt</CockpitSectionLabel><h2 id="create-media-title" className="mt-1 text-lg font-semibold text-[#e8eef8]">Produktionsworkspace anlegen</h2></header>
          <div className="space-y-3 p-4">
            <label className="block text-xs text-[#8d9ab0]">Name<input autoFocus value={createName} onChange={(event) => setCreateName(event.target.value)} className="mt-1 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]" /></label>
            <label className="block text-xs text-[#8d9ab0]">Beschreibung<textarea value={createDescription} onChange={(event) => setCreateDescription(event.target.value)} rows={4} className="mt-1 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]" /></label>
            <p className="text-xs leading-4 text-[#8d9ab0]">Wird sicher im Workspace des gewählten Heimatprojekts unter <code>media/&lt;slug&gt;</code> angelegt. Kein Generator- oder LLM-Job wird gestartet.</p>
            {createError && <p className="text-sm text-[#fb7185]">{createError}</p>}
          </div>
          <footer className="flex justify-end gap-2 border-t border-[#2a364b] p-3"><CockpitButton onClick={() => setCreateOpen(false)}>Schließen</CockpitButton><CockpitButton tone="primary" onClick={createMediaProject}>Anlegen</CockpitButton></footer>
        </section>
      </div>}
    </CockpitShell>
  )
}

function statusColor(status: VideoJob["status"] | FilmJob["status"]) {
  if (status === "completed") return "#4ade80"
  if (status === "failed") return "#fb7185"
  if (status === "processing") return "#69d7ff"
  return "#fbbf24"
}

function TimelineTrack({ label, clips }: { label: string; clips: Array<{ left: number; width: number; color?: string }> }) {
  return <div className="grid grid-cols-[70px_1fr] items-center gap-2"><span className="text-xs text-[#8d9ab0]">{label}</span><div className="relative h-5 rounded-[2px] border border-[#2a364b] bg-[#0d1420]">{clips.map((clip, index) => <div key={index} className="absolute top-0 h-full rounded-[2px] bg-[linear-gradient(90deg,#ffb86b,#c084fc)]" style={{ left: `${clip.left}%`, width: `${clip.width}%`, background: clip.color }} />)}</div></div>
}
