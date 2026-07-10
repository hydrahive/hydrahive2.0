import { Film, FolderOpen, Images, Mic2, Music2, Palette, PlaySquare, Scissors, Sparkles, Wand2 } from "lucide-react"
import { CockpitButton } from "./CockpitButton"
import { CockpitPanel, CockpitSectionLabel } from "./CockpitPanel"
import { CockpitShell } from "./CockpitShell"
import { CockpitTopbar } from "./CockpitTopbar"

const pipeline = [
  { label: "Idee", text: "Prompt, Mood, Stil und CI sammeln", icon: Sparkles },
  { label: "Regie", text: "Szenen, Shots, Dialoge und Kamera planen", icon: Film },
  { label: "Assets", text: "Charaktere, Referenzen, Bilder und Audio", icon: Images },
  { label: "Clips", text: "Video-Jobs, Continue-Frames und Varianten", icon: Wand2 },
  { label: "Schnitt", text: "Timeline, Film Composer und Export", icon: Scissors },
]

const quickLinks = [
  { title: "Atelier öffnen", desc: "Bild, Charaktere, Regie, Video, Audio und Film Composer", path: "/atelier", icon: Palette, primary: true },
  { title: "Streaming", desc: "Medien-Downloads und Plex/Streaming-Helfer", path: "/streaming", icon: Film },
  { title: "Musikplayer", desc: "Musik-Modul und generierte Tracks", path: "/musicplayer", icon: Music2 },
]

const assetAreas = [
  { title: "Charaktere", body: "Figuren, Referenzbilder und wiederverwendbare Looks aus dem Atelier.", icon: Images },
  { title: "Bildwelten", body: "Generierte Frames, Stiltests, CI-Varianten und Keyframes.", icon: Palette },
  { title: "Video-Clips", body: "Einzelclips, Continue-Jobs und Szenenvarianten.", icon: Film },
  { title: "Audio", body: "Musik, Voiceover, Soundbeds und spätere Mixdowns.", icon: Mic2 },
]

const workbenchLinks = [
  { title: "Atelier-Projekte", path: "/atelier", icon: FolderOpen, text: "Ideen, Charaktere, Stile und Regie-Arbeit öffnen." },
  { title: "Clips prüfen", path: "/atelier", icon: PlaySquare, text: "Video-Jobs, Continue-Frames und Varianten über das Atelier verfolgen." },
  { title: "Soundtrack", path: "/musicplayer", icon: Music2, text: "Generierte Musik importieren, abspielen und sortieren." },
  { title: "Streaming", path: "/streaming", icon: Film, text: "Downloads und Streaming-Helfer im Blick behalten." },
]

export function MediaCockpitPage() {
  return (
    <CockpitShell
      eyebrow="Media"
      title="Media-Cockpit"
      description="Produktionsstrecke von Idee und Regie über Assets und Clips bis zum Schnitt. Diese Etappe verknüpft vorhandene Module ohne automatische Generierungsjobs."
      actions={<CockpitButton tone="primary" onClick={() => window.open("/atelier", "_self")}>Atelier öffnen</CockpitButton>}
      className="flex h-[100dvh] min-h-0 flex-col overflow-hidden bg-[#080b11]"
      hideHeader
    >
      <CockpitTopbar active="media" context="Projekt: HydraHive DEV" action={{ label: "Atelier öffnen", path: "/atelier" }} />
      <div className="grid min-h-0 flex-1 gap-[10px] overflow-hidden p-[10px] xl:grid-cols-[280px_minmax(520px,1fr)_360px]">
        <aside className="space-y-[10px]">
          <CockpitPanel title="Schnellstart" eyebrow="Module">
            <div className="space-y-2">
              {quickLinks.map((item) => {
                const Icon = item.icon
                return (
                  <button
                    key={item.path}
                    onClick={() => window.open(item.path, "_self")}
                    className={["group flex w-full items-start gap-3 rounded-[4px] border p-3 text-left transition-colors", item.primary ? "border-[#69d7ff]/45 bg-[#1c2940]" : "border-[#2a364b] bg-[#111827] hover:border-[#46617f] hover:bg-[#172133]"].join(" ")}
                  >
                    <Icon size={18} className={item.primary ? "mt-0.5 text-[#69d7ff]" : "mt-0.5 text-[#8d9ab0] group-hover:text-[#e8eef8]"} />
                    <span className="min-w-0">
                      <span className="block text-sm font-bold text-[#e8eef8]">{item.title}</span>
                      <span className="mt-1 block text-xs leading-4 text-[#8d9ab0]">{item.desc}</span>
                    </span>
                  </button>
                )
              })}
            </div>
          </CockpitPanel>

          <CockpitPanel title="Modelle" eyebrow="Generatoren">
            <div className="space-y-2 text-xs text-[#8d9ab0]">
              <p><span className="font-semibold text-[#e8eef8]">Bild:</span> OpenAI/Gemini Bildmodelle über Atelier.</p>
              <p><span className="font-semibold text-[#e8eef8]">Video:</span> Hailuo/Kling/Seedance/Veo über Video-Jobs.</p>
              <p><span className="font-semibold text-[#e8eef8]">Musik:</span> Lyria/Music-Modul.</p>
              <p><span className="font-semibold text-[#e8eef8]">Voice:</span> TTS/Voiceover über Medien-Tools.</p>
            </div>
          </CockpitPanel>
        </aside>

        <main className="space-y-[10px]">
          <CockpitPanel title="Produktions-Pipeline" eyebrow="Storyboard">
            <div className="grid gap-2 md:grid-cols-5">
              {pipeline.map((step, index) => {
                const Icon = step.icon
                return (
                  <div key={step.label} className="rounded-[4px] border border-[#2a364b] bg-[#111827] p-3">
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <Icon size={16} className="text-[#69d7ff]" />
                      <span className="font-mono text-[10px] text-[#8d9ab0]">0{index + 1}</span>
                    </div>
                    <h3 className="text-sm font-black text-[#e8eef8]">{step.label}</h3>
                    <p className="mt-1 text-xs leading-4 text-[#8d9ab0]">{step.text}</p>
                  </div>
                )
              })}
            </div>
          </CockpitPanel>

          <CockpitPanel title="Assets & Bibliothek" eyebrow="Material">
            <div className="grid gap-2 md:grid-cols-2">
              {assetAreas.map((area) => {
                const Icon = area.icon
                return (
                  <div key={area.title} className="rounded-[4px] border border-white/[8%] bg-white/[3%] p-3">
                    <div className="mb-2 flex items-center gap-2">
                      <Icon size={15} className="text-[#69d7ff]" />
                      <h3 className="text-sm font-bold text-[#e8eef8]">{area.title}</h3>
                    </div>
                    <p className="text-xs leading-4 text-[#8d9ab0]">{area.body}</p>
                  </div>
                )
              })}
            </div>
          </CockpitPanel>

          <CockpitPanel title="Arbeitsflächen" eyebrow="Workbench">
            <div className="grid gap-2 md:grid-cols-4">
              {workbenchLinks.map((item) => {
                const Icon = item.icon
                return (
                  <button key={item.title} onClick={() => window.open(item.path, "_self")} className="rounded-[4px] border border-[#2a364b] bg-[#111827] p-3 text-left hover:border-[#46617f] hover:bg-[#172133]">
                    <Icon size={16} className="mb-2 text-[#69d7ff]" />
                    <h3 className="text-sm font-bold text-[#e8eef8]">{item.title}</h3>
                    <p className="mt-1 text-xs leading-4 text-[#8d9ab0]">{item.text}</p>
                  </button>
                )
              })}
            </div>
          </CockpitPanel>

          <CockpitPanel title="Regie-Ebene" eyebrow="Planung">
            <div className="rounded-[4px] border border-amber-400/20 bg-amber-500/[6%] p-3 text-sm leading-5 text-[#d7deea]">
              <p>
                Der Regie-/Drehbuchplaner bleibt als größere Folgeetappe im Atelier-Modul geplant. Dieses Cockpit ist jetzt der stabile Einstiegspunkt: Es bündelt die bestehende Produktion und hält die Pipeline sichtbar, ohne automatisch LLM- oder Medienjobs zu starten.
              </p>
              <div className="mt-3 flex gap-2">
                <CockpitButton onClick={() => window.open("/atelier", "_self")}>Zur Regie im Atelier</CockpitButton>
                <CockpitButton onClick={() => window.open("/mockups/media-cockpit-v1/index.html", "_blank")}>Mockup öffnen</CockpitButton>
              </div>
            </div>
          </CockpitPanel>
        </main>

        <aside className="space-y-[10px]">
          <CockpitPanel title="Aktuelle Etappe" eyebrow="Status">
            <CockpitSectionLabel>Design</CockpitSectionLabel>
            <p className="mt-2 text-sm leading-5 text-[#d7deea]">
              Media ist jetzt kein leerer Platzhalter mehr. Die Seite ist eine sichere Schaltzentrale zu Atelier, Video, Audio und Schnitt.
            </p>
            <ul className="mt-3 space-y-1 text-xs text-[#8d9ab0]">
              <li>• keine versteckten Generierungsjobs</li>
              <li>• keine automatischen LLM-Calls</li>
              <li>• vorhandene Module bleiben Quelle der Wahrheit</li>
              <li>• Pipeline bereit für echte Regie-Integration</li>
            </ul>
          </CockpitPanel>

          <CockpitPanel title="Nächste Ausbaustufen" eyebrow="Roadmap">
            <ol className="space-y-2 text-xs leading-4 text-[#8d9ab0]">
              <li><span className="font-semibold text-[#e8eef8]">1.</span> Atelier-Projektstatus live laden.</li>
              <li><span className="font-semibold text-[#e8eef8]">2.</span> Regie/Szenen direkt im Cockpit editieren.</li>
              <li><span className="font-semibold text-[#e8eef8]">3.</span> Asset-Bibliothek als echte Galerie einbetten.</li>
              <li><span className="font-semibold text-[#e8eef8]">4.</span> Timeline/Videoeditor als Panel einhängen.</li>
            </ol>
          </CockpitPanel>
        </aside>
      </div>
    </CockpitShell>
  )
}
