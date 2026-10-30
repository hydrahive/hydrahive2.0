import { useEffect, useMemo, useState } from "react"
import { Film, Images, Scissors, Sparkles, Users, Video } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { projectsApi } from "@/features/projects/api"
import { ownProjects } from "@/features/projects/membership"
import type { Project } from "@/features/projects/types"
import { TileIcon } from "@/shared/brand/TileIcon"
import { CockpitSectionLabel } from "./CockpitPanel"
import { CockpitShell } from "./CockpitShell"
import { CockpitTopbar } from "./CockpitTopbar"
import { MediaPostProduction } from "./media/MediaPostProduction"
import { primaryMediaWorkflow } from "./media/mediaRegistry"

/** Aktive Ansicht: eine Schritt-ID des Modul-Workflows oder der Videoschnitt.
 *  Die Schritte liefert das Modul, deshalb ist die ID nicht mehr fest bekannt. */
type MediaView = string

const ICONS: Record<string, typeof Users> = { characters: Users, generate: Sparkles, gallery: Images, clips: Video, film: Film }

/** Produktions-Workflow aus einem Modul (Atelier). Nicht installiert → null;
 *  das Cockpit zeigt dann nur den Videoschnitt. Erst beim Rendern lesen
 *  (Lade-Schleife, Task 08c5c546). */
function useWorkflow() {
  return useMemo(() => {
    const workflow = primaryMediaWorkflow()
    const steps = (workflow?.steps ?? []).map((step, index) => ({
      id: step.id,
      number: String(index + 1).padStart(2, "0"),
      title: step.title,
      text: step.text,
      icon: ICONS[step.icon ?? step.id] ?? Sparkles,
    }))
    return { workflow, WorkflowPage: workflow?.component ?? null, steps }
  }, [])
}

export function MediaCockpitPage() {
  const { workflow, WorkflowPage, steps } = useWorkflow()
  const username = useAuthStore((s) => s.username)
  const [projects, setProjects] = useState<Project[] | null>(null)
  const [projectId, setProjectId] = useState("")
  // Ohne Produktions-Workflow (Modul fehlt) startet das Cockpit direkt im Schnitt.
  const [view, setView] = useState<MediaView>(workflow ? "generate" : "editor")

  useEffect(() => {
    // Nur eigene Projekte: Admins bekommen von /api/projects alle, Atelier/Studio
    // erlauben aber nur Mitglieder (sonst „Projekt nicht gefunden“, Task 308b7c91).
    projectsApi.list().then((all) => {
      const items = ownProjects(all, username)
      setProjects(items)
      setProjectId((current) => (items.some((p) => p.id === current) ? current : items[0]?.id || ""))
    })
  }, [username])

  const project = useMemo(() => projects?.find((item) => item.id === projectId), [projects, projectId])
  const isEditor = view === "editor" || !WorkflowPage
  const activeIndex = steps.findIndex((item) => item.id === view)
  const activeStep = steps[activeIndex]

  return (
    <CockpitShell title="Media-Cockpit" eyebrow="Media" description="Geführter Produktionsablauf" hideHeader className="flex h-full min-h-0 flex-col overflow-hidden bg-s-grund">
      <CockpitTopbar active="media" context={project?.name ?? "Projekt laden…"} action={workflow ? { label: "Atelier", path: "/atelier" } : undefined} />
      <div className="grid min-h-0 flex-1 gap-[10px] overflow-hidden p-[10px] lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="panel min-h-0 overflow-y-auto rounded-[4px] border border-s-rand bg-s-box p-3">
          <CockpitSectionLabel>Projekt</CockpitSectionLabel>
          <select aria-label="Projekt" value={projectId} onChange={(event) => setProjectId(event.target.value)} className="mt-2 w-full rounded-[4px] border border-s-rand bg-s-tief px-3 py-2 text-sm text-[#e8eef8]">
            {projects === null && <option value="">Projekte laden…</option>}
            {projects?.length === 0 && <option value="">Kein eigenes Projekt</option>}
            {projects?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>

          {steps.length > 0 && <>
          <div className="mt-5 flex items-center justify-between gap-2">
            <CockpitSectionLabel>Produktion</CockpitSectionLabel>
            <span className="font-mono text-[10px] text-[#9aa7bc]">{activeIndex >= 0 ? activeIndex + 1 : "–"} / {steps.length}</span>
          </div>
          <nav className="mt-2 space-y-2" aria-label="Produktionsschritte">
            {steps.map((item, index) => {
              const Icon = item.icon
              const active = item.id === view
              return (
                <button key={item.id} onClick={() => setView(item.id)} className={["grid w-full grid-cols-[32px_1fr] gap-2 rounded-[4px] border p-2 text-left transition-colors", active ? "border-[#ffb86b]/55 bg-[#30243a]" : "border-s-rand bg-s-innen hover:border-s-rand-hover"].join(" ")}>
                  <span className={["grid h-8 w-8 place-items-center rounded-[3px] border", active ? "border-[#ffb86b]/50 bg-[#ffb86b]/10 text-[#ffb86b]" : "border-s-rand bg-s-tief text-[#9aa7bc]"].join(" ")}><TileIcon target={`media:${item.id}`} icon={Icon} size="sm" iconSize={15} iconClassName="" /></span>
                  <span className="min-w-0"><span className="flex items-center justify-between gap-2"><strong className="text-sm text-[#e8eef8]">{item.title}</strong><span className="font-mono text-[10px] text-[#9aa7bc]">{item.number}</span></span><span className="block text-xs leading-4 text-[#9aa7bc]">{item.text}</span>{activeIndex >= 0 && index < activeIndex && <span className="mt-1 block text-[10px] uppercase tracking-[0.12em] text-[#4ade80]">durchlaufen</span>}</span>
                </button>
              )
            })}
          </nav>
          </>}

          {/* Trenner + eigener Menüpunkt Nachbearbeitung */}
          <div className="mt-5 border-t border-s-rand pt-4">
            <CockpitSectionLabel>Nachbearbeitung</CockpitSectionLabel>
            <button onClick={() => setView("editor")} className={["mt-2 grid w-full grid-cols-[32px_1fr] gap-2 rounded-[4px] border p-2 text-left transition-colors", isEditor ? "border-[#ffb86b]/55 bg-[#30243a]" : "border-s-rand bg-s-innen hover:border-s-rand-hover"].join(" ")}>
              <span className={["grid h-8 w-8 place-items-center rounded-[3px] border", isEditor ? "border-[#ffb86b]/50 bg-[#ffb86b]/10 text-[#ffb86b]" : "border-s-rand bg-s-tief text-[#9aa7bc]"].join(" ")}><TileIcon target="media:editor" icon={Scissors} size="sm" iconSize={15} iconClassName="" /></span>
              <span className="min-w-0"><strong className="text-sm text-[#e8eef8]">Videoschnitt</strong><span className="block text-xs leading-4 text-[#9aa7bc]">Clips schneiden und vertonen</span></span>
            </button>
          </div>
        </aside>

        <main className="panel grid min-h-0 grid-rows-[auto_1fr] overflow-hidden rounded-[4px] border border-s-rand bg-s-box">
          <header className="border-b border-s-rand bg-s-kopf px-4 py-3">
            {isEditor ? (
              <>
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#ffb86b]">Nachbearbeitung</span>
                <h1 className="mt-1 text-lg font-semibold text-[#e8eef8]">Videoschnitt</h1>
                <p className="mt-1 text-xs text-[#9aa7bc]">Clips auf Spuren schneiden, vertonen und exportieren</p>
              </>
            ) : (
              <>
                <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#ffb86b]">Schritt {String(activeIndex + 1).padStart(2, "0")}</span>
                <h1 className="mt-1 text-lg font-semibold text-[#e8eef8]">{activeStep?.title}</h1>
                <p className="mt-1 text-xs text-[#9aa7bc]">{activeStep?.text}</p>
              </>
            )}
          </header>
          <div className="min-h-0 overflow-y-auto p-4">
            {isEditor || !WorkflowPage
              ? <MediaPostProduction projectId={projectId} />
              : <WorkflowPage projectId={projectId} step={view} onStepChange={setView} hideHeader />}
          </div>
        </main>
      </div>
    </CockpitShell>
  )
}
