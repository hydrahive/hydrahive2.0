import { useEffect, useMemo, useState, type ComponentType } from "react"
import { Film, Images, Sparkles, Users, Video } from "lucide-react"
import { projectsApi } from "@/features/projects/api"
import type { Project } from "@/features/projects/types"
import { AtelierPage } from "@/modules/atelier/AtelierPage"
import { CockpitSectionLabel } from "./CockpitPanel"
import { CockpitShell } from "./CockpitShell"
import { CockpitTopbar } from "./CockpitTopbar"

type AtelierStep = "characters" | "generate" | "gallery" | "clips" | "film"
type ControlledAtelierProps = { projectId?: string; step?: AtelierStep; onStepChange?: (step: AtelierStep) => void; hideHeader?: boolean }
const ControlledAtelierPage = AtelierPage as ComponentType<ControlledAtelierProps>

const steps = [
  { id: "characters", number: "01", title: "Charaktere", text: "Figuren auswählen und verwalten", icon: Users },
  { id: "generate", number: "02", title: "Bild erzeugen", text: "Keyframes und Motive erstellen", icon: Sparkles },
  { id: "gallery", number: "03", title: "Galerie", text: "Bilder ansehen und weiterverwenden", icon: Images },
  { id: "clips", number: "04", title: "Videoclips", text: "Clips erzeugen und abspielen", icon: Video },
  { id: "film", number: "05", title: "Film erstellen", text: "Clips ordnen und Film rendern", icon: Film },
] as const

export function MediaCockpitPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState("")
  const [step, setStep] = useState<AtelierStep>("generate")

  useEffect(() => {
    projectsApi.list().then((items) => {
      setProjects(items)
      setProjectId((current) => current || items[0]?.id || "")
    })
  }, [])

  const project = useMemo(() => projects.find((item) => item.id === projectId), [projects, projectId])
  const activeIndex = steps.findIndex((item) => item.id === step)

  return (
    <CockpitShell title="Media-Cockpit" eyebrow="Media" description="Geführter Produktionsablauf" hideHeader className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]">
      <CockpitTopbar active="media" context={project?.name ?? "Projekt laden…"} action={{ label: "Atelier", path: "/atelier" }} />
      <div className="grid min-h-0 flex-1 gap-[10px] overflow-hidden p-[10px] lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="panel min-h-0 overflow-y-auto rounded-[4px] border border-[#2a364b] bg-[#151c2b] p-3">
          <CockpitSectionLabel>Projekt</CockpitSectionLabel>
          <select value={projectId} onChange={(event) => setProjectId(event.target.value)} className="mt-2 w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]">
            {projects.length === 0 && <option value="">Projekte laden…</option>}
            {projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>

          <div className="mt-5 flex items-center justify-between gap-2">
            <CockpitSectionLabel>Produktion</CockpitSectionLabel>
            <span className="font-mono text-[10px] text-[#8d9ab0]">{activeIndex + 1} / {steps.length}</span>
          </div>
          <nav className="mt-2 space-y-2" aria-label="Produktionsschritte">
            {steps.map((item, index) => {
              const Icon = item.icon
              const active = item.id === step
              return (
                <button key={item.id} onClick={() => setStep(item.id)} className={["grid w-full grid-cols-[32px_1fr] gap-2 rounded-[4px] border p-2 text-left transition-colors", active ? "border-[#ffb86b]/55 bg-[#30243a]" : "border-[#2a364b] bg-[#111827] hover:border-[#46617f]"].join(" ")}>
                  <span className={["grid h-8 w-8 place-items-center rounded-[3px] border", active ? "border-[#ffb86b]/50 bg-[#ffb86b]/10 text-[#ffb86b]" : "border-[#2a364b] bg-[#0d1420] text-[#8d9ab0]"].join(" ")}><Icon size={15} /></span>
                  <span className="min-w-0"><span className="flex items-center justify-between gap-2"><strong className="text-sm text-[#e8eef8]">{item.title}</strong><span className="font-mono text-[10px] text-[#68758a]">{item.number}</span></span><span className="block text-xs leading-4 text-[#8d9ab0]">{item.text}</span>{index < activeIndex && <span className="mt-1 block text-[10px] uppercase tracking-[0.12em] text-[#4ade80]">durchlaufen</span>}</span>
                </button>
              )
            })}
          </nav>
        </aside>

        <main className="panel grid min-h-0 grid-rows-[auto_1fr] overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#151c2b]">
          <header className="border-b border-[#2a364b] bg-[#111827] px-4 py-3">
            <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#ffb86b]">Schritt {String(activeIndex + 1).padStart(2, "0")}</span>
            <h1 className="mt-1 text-lg font-semibold text-[#e8eef8]">{steps[activeIndex]?.title}</h1>
            <p className="mt-1 text-xs text-[#8d9ab0]">{steps[activeIndex]?.text}</p>
          </header>
          <div className="min-h-0 overflow-hidden p-4"><ControlledAtelierPage projectId={projectId} step={step} onStepChange={setStep} hideHeader /></div>
        </main>
      </div>
    </CockpitShell>
  )
}
