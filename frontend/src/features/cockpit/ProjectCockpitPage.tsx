import { useEffect, useMemo, useState } from "react"
import { ChatPane } from "@/features/chat/ChatPane"
import { chatApi } from "@/features/chat/api"
import type { AgentBrief } from "@/features/chat/types"
import { FileOverlay } from "@/features/chat/workspace/FileOverlay"
import type { FileKind } from "@/features/chat/workspace/fileType"
import { projectsApi } from "@/features/projects/api"
import type { Project } from "@/features/projects/types"
import { useUserPreferences } from "@/features/preferences/useUserPreferences"
import { CockpitButton } from "./CockpitButton"
import { CockpitPanel } from "./CockpitPanel"
import { CockpitShell } from "./CockpitShell"
import { ProjectAgentsPanel } from "./project/ProjectAgentsPanel"
import { ProjectFilesPanel } from "./project/ProjectFilesPanel"
import { ProjectGitSummary } from "./project/ProjectGitSummary"
import { ProjectSelector } from "./project/ProjectSelector"
import { ProjectTasksPanel } from "./project/ProjectTasksPanel"

export function ProjectCockpitPage() {
  const prefs = useUserPreferences()
  const [projects, setProjects] = useState<Project[]>([])
  const [agents, setAgents] = useState<AgentBrief[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [wsFile, setWsFile] = useState<{ path: string; kind: FileKind } | null>(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    Promise.all([projectsApi.list(), chatApi.listAgents()])
      .then(([projectList, agentList]) => {
        if (!alive) return
        setProjects(projectList)
        setAgents(agentList)
        setError(null)
      })
      .catch(() => { if (alive) setError("Projekt-Cockpit konnte nicht geladen werden.") })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  const activeProjectId = useMemo(() => {
    const preferred = prefs.preferences.active_project_id
    if (preferred && projects.some((p) => p.id === preferred)) return preferred
    return projects[0]?.id ?? null
  }, [prefs.preferences.active_project_id, projects])

  useEffect(() => {
    if (!activeProjectId || prefs.loading) return
    if (prefs.preferences.active_project_id !== activeProjectId) {
      void prefs.patch({ active_project_id: activeProjectId })
    }
  }, [activeProjectId, prefs.loading, prefs.preferences.active_project_id, prefs.patch])

  const activeProject = projects.find((p) => p.id === activeProjectId) ?? null
  const projectAgentId = activeProject?.agent_id ?? null

  async function pickProject(projectId: string | null) {
    await prefs.patch({ active_project_id: projectId })
  }

  return (
    <CockpitShell
      eyebrow="Projekte"
      title="Projekt-Cockpit"
      description="Alles Projektbezogene an einem Ort: Chat, Agenten, Git, Dateien, Tasks und später Datamining."
      actions={(
        <>
          <CockpitButton onClick={() => window.open("/settings/projects", "_self")}>Projekt-Einstellungen</CockpitButton>
          <CockpitButton tone="primary" onClick={() => window.open("/werkstatt", "_self")}>Alte Werkstatt</CockpitButton>
        </>
      )}
      className="h-full"
    >
      {error && <div className="rounded-[4px] border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{error}</div>}
      <div className="grid min-h-[calc(100dvh-11rem)] gap-3 xl:grid-cols-[280px_minmax(420px,1fr)_360px]">
        <aside className="space-y-3 overflow-hidden">
          <CockpitPanel>
            <ProjectSelector projects={projects} activeProjectId={activeProjectId} loading={loading || prefs.loading} onPick={pickProject} />
            {activeProject && <p className="mt-3 line-clamp-3 text-xs text-zinc-500">{activeProject.description || "Keine Beschreibung."}</p>}
          </CockpitPanel>
          <ProjectAgentsPanel agents={agents} projectAgentId={projectAgentId} />
          <ProjectGitSummary projectId={activeProjectId} />
          <CockpitPanel title="KI Einstellungen" eyebrow="Chat">
            <p className="text-xs text-zinc-500">Modell und Tiefe bleiben im Chat/Agenten-Kontext. Die vollständigen Controls werden in der nächsten ChatPane-Etappe eingebettet.</p>
          </CockpitPanel>
        </aside>

        <main className="min-h-[620px] overflow-hidden rounded-[4px] border border-white/[8%] bg-zinc-950/40">
          {activeProjectId ? (
            <ChatPane projectId={activeProjectId} showSidePanels={false} preferredAgentId={projectAgentId} />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-zinc-600">Bitte ein Projekt auswählen.</div>
          )}
        </main>

        <aside className="grid min-h-0 gap-3 overflow-hidden xl:grid-rows-[minmax(0,1fr)_auto]">
          <ProjectFilesPanel agentId={projectAgentId} projectId={activeProjectId} onOpenFile={(path, kind) => setWsFile({ path, kind })} />
          <ProjectTasksPanel projectId={activeProjectId} />
        </aside>
      </div>
      {wsFile && projectAgentId && (
        <FileOverlay agentId={projectAgentId} path={wsFile.path} kind={wsFile.kind} onClose={() => setWsFile(null)} />
      )}
    </CockpitShell>
  )
}
