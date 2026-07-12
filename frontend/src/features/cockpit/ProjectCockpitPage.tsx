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
import { CollapsibleCockpitPanel } from "./project/CollapsibleCockpitPanel"
import { CockpitShell } from "./CockpitShell"
import { CockpitTopbar } from "./CockpitTopbar"
import { ProjectAgentEditOverlay } from "./project/ProjectAgentEditOverlay"
import { ProjectCreateOverlay } from "./project/ProjectCreateOverlay"
import { ProjectDetailsOverlay } from "./project/ProjectDetailsOverlay"
import { ProjectAccessOverlay } from "./project/ProjectAccessOverlay"
import { ProjectServersOverlay } from "./project/ProjectServersOverlay"
import { ProjectMountsOverlay } from "./project/ProjectMountsOverlay"
import { ProjectInsightsOverlay, type ProjectInsightView } from "./project/ProjectInsightsOverlay"
import { ProjectAgentsPanel } from "./project/ProjectAgentsPanel"
import { ProjectAiSettingsPanel } from "./project/ProjectAiSettingsPanel"
import { CockpitUsagePanel } from "./project/CockpitUsagePanel"
import { ProjectGitSummary } from "./project/ProjectGitSummary"
import { ProjectGitOverlay } from "./project/ProjectGitOverlay"
import { ProjectGraphOverlay } from "./project/ProjectGraphOverlay"
import { ProjectIntegrationsOverlay } from "./project/ProjectIntegrationsOverlay"
import { ProjectGitTreePanel } from "./project/ProjectGitTreePanel"
import { ProjectWorkspacePanel } from "./project/ProjectWorkspacePanel"
import { ProjectSelector } from "./project/ProjectSelector"
import { ProjectTasksPanel } from "./project/ProjectTasksPanel"
import { ProjectActionGroups } from "./project/ProjectActionGroups"

export function ProjectCockpitPage() {
  const prefs = useUserPreferences()
  const [projects, setProjects] = useState<Project[]>([])
  const [agents, setAgents] = useState<AgentBrief[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [wsFile, setWsFile] = useState<{ path: string; kind: FileKind } | null>(null)
  const [editingAgentId, setEditingAgentId] = useState<string | null>(null)
  const [createProjectOpen, setCreateProjectOpen] = useState(false)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [accessOpen, setAccessOpen] = useState(false)
  const [serversOpen, setServersOpen] = useState(false)
  const [mountsOpen, setMountsOpen] = useState(false)
  const [insightView, setInsightView] = useState<ProjectInsightView | null>(null)
  const [gitOpen, setGitOpen] = useState(false)
  const [graphOpen, setGraphOpen] = useState(false)
  const [gitRevision, setGitRevision] = useState(0)
  const [integrationsOpen, setIntegrationsOpen] = useState(false)
  const [selectedAgentByProject, setSelectedAgentByProject] = useState<Record<string, string>>({})

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
  const selectedAgentId = activeProjectId ? (selectedAgentByProject[activeProjectId] ?? projectAgentId) : projectAgentId
  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId) ?? null
  const selectedAgentModel = selectedAgent?.llm_model ?? ""
  type LeftPanelId = "project" | "agents" | "git" | "ai" | "usage"
  const leftPanelDefaults: Record<LeftPanelId, boolean> = { project: false, agents: false, git: true, ai: true, usage: false }
  const leftPanelCollapsed = { ...leftPanelDefaults, ...((prefs.preferences.cockpit_layout?.project_left_collapsed ?? {}) as Partial<Record<LeftPanelId, boolean>>) }
  const setLeftPanelCollapsed = (panel: LeftPanelId, collapsed: boolean) => {
    void prefs.patch({
      cockpit_layout: {
        ...prefs.preferences.cockpit_layout,
        project_left_collapsed: { ...leftPanelCollapsed, [panel]: collapsed },
      },
    })
  }

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
          <CockpitButton tone="primary" onClick={() => setCreateProjectOpen(true)}>+ Neues Projekt</CockpitButton>
        </>
      )}
      className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]"
      hideHeader
    >
      <CockpitTopbar
        active="projects"
        context={activeProject ? `Projekt bleibt gespeichert: ${activeProject.name}` : undefined}
      />
      {error && <div className="mx-[10px] mt-[10px] shrink-0 rounded-[4px] border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{error}</div>}
      <div className="grid min-h-0 flex-1 gap-[10px] overflow-hidden p-[10px] xl:grid-cols-[270px_minmax(420px,1fr)_360px]">
        <aside className="min-h-0 space-y-[10px] overflow-y-auto pr-1">
          <CollapsibleCockpitPanel
            title="Projekt"
            eyebrow="Projekt"
            summary={activeProject?.name ?? "Kein Projekt"}
            collapsed={leftPanelCollapsed.project}
            onToggle={() => setLeftPanelCollapsed("project", !leftPanelCollapsed.project)}
          >
            <ProjectSelector projects={projects} activeProjectId={activeProjectId} loading={loading || prefs.loading} onPick={pickProject} />
            {activeProject && <p className="mt-3 line-clamp-3 text-xs text-[#8d9ab0]">{activeProject.description || "Keine Beschreibung."}</p>}
            <ProjectActionGroups
              disabled={!activeProject}
              onCreate={() => setCreateProjectOpen(true)}
              onEdit={() => setDetailsOpen(true)}
              onAccess={() => setAccessOpen(true)}
              onServers={() => setServersOpen(true)}
              onMounts={() => setMountsOpen(true)}
              onGit={() => setGitOpen(true)}
              onIntegrations={() => setIntegrationsOpen(true)}
              onInsight={setInsightView}
              onGraph={() => setGraphOpen(true)}
            />
          </CollapsibleCockpitPanel>

          <CollapsibleCockpitPanel
            title="Projekt-Agenten"
            eyebrow="Agenten"
            summary={selectedAgent?.name ?? "Kein Agent"}
            collapsed={leftPanelCollapsed.agents}
            onToggle={() => setLeftPanelCollapsed("agents", !leftPanelCollapsed.agents)}
          >
            <ProjectAgentsPanel
              agents={agents}
              projectAgentId={projectAgentId}
              selectedAgentId={selectedAgentId}
              onSelect={(agentId) => {
                if (!activeProjectId) return
                setSelectedAgentByProject((cur) => ({ ...cur, [activeProjectId]: agentId }))
              }}
              onEdit={setEditingAgentId}
            />
          </CollapsibleCockpitPanel>

          <CollapsibleCockpitPanel
            title="Git Status"
            eyebrow="Git"
            summary="Repository-Status"
            collapsed={leftPanelCollapsed.git}
            onToggle={() => setLeftPanelCollapsed("git", !leftPanelCollapsed.git)}
          >
            <ProjectGitSummary key={`${activeProjectId}:${gitRevision}`} projectId={activeProjectId} />
          </CollapsibleCockpitPanel>

          <CollapsibleCockpitPanel
            title="KI Einstellungen"
            eyebrow="Chat"
            summary={selectedAgentModel || "Kein Modell"}
            collapsed={leftPanelCollapsed.ai}
            onToggle={() => setLeftPanelCollapsed("ai", !leftPanelCollapsed.ai)}
          >
            <ProjectAiSettingsPanel
              agentId={projectAgentId}
              agents={agents}
              onAgentChanged={(updated) => setAgents((cur) => cur.map((agent) => agent.id === updated.id ? { ...agent, ...updated } : agent))}
            />
          </CollapsibleCockpitPanel>

          <CollapsibleCockpitPanel
            title="Verbrauch"
            eyebrow="Guthaben"
            summary="Modell-Kontingente"
            collapsed={leftPanelCollapsed.usage}
            onToggle={() => setLeftPanelCollapsed("usage", !leftPanelCollapsed.usage)}
          >
            <CockpitUsagePanel />
          </CollapsibleCockpitPanel>
        </aside>

        <main className="min-h-0 overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#151c2b]">
          {activeProjectId ? (
            <ChatPane key={`${activeProjectId}:${selectedAgentId}:${selectedAgentModel}`} projectId={activeProjectId} showSidePanels={false} preferredAgentId={selectedAgentId} />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-zinc-600">Bitte ein Projekt auswählen.</div>
          )}
        </main>

        <aside className="grid min-h-0 gap-[10px] overflow-hidden xl:grid-rows-[32fr_38fr_30fr]">
          <ProjectGitTreePanel projectId={activeProjectId} />
          <ProjectWorkspacePanel projectId={activeProjectId} onOpenFile={(path, kind) => setWsFile({ path, kind })} />
          <ProjectTasksPanel projectId={activeProjectId} />
        </aside>
      </div>
      {wsFile && projectAgentId && (
        <FileOverlay agentId={projectAgentId} path={wsFile.path} kind={wsFile.kind} onClose={() => setWsFile(null)} />
      )}
      {integrationsOpen && activeProject && <ProjectIntegrationsOverlay project={activeProject} onClose={() => setIntegrationsOpen(false)} onSaved={(updated) => setProjects((current) => current.map((project) => project.id === updated.id ? updated : project))} />}
      {gitOpen && activeProject && <ProjectGitOverlay project={activeProject} onClose={() => setGitOpen(false)} onChanged={() => setGitRevision((revision) => revision + 1)} />}
      {insightView && activeProject && <ProjectInsightsOverlay project={activeProject} view={insightView} onClose={() => setInsightView(null)} />}
      {graphOpen && activeProject && <ProjectGraphOverlay project={activeProject} onClose={() => setGraphOpen(false)} />}
      {mountsOpen && activeProject && <ProjectMountsOverlay project={activeProject} onClose={() => setMountsOpen(false)} />}
      {serversOpen && activeProject && <ProjectServersOverlay project={activeProject} onClose={() => setServersOpen(false)} />}
      {accessOpen && activeProject && (
        <ProjectAccessOverlay
          project={activeProject}
          onClose={() => setAccessOpen(false)}
          onChanged={(updated) => setProjects((current) => current.map((project) => project.id === updated.id ? updated : project))}
        />
      )}
      {detailsOpen && activeProject && (
        <ProjectDetailsOverlay
          project={activeProject}
          onClose={() => setDetailsOpen(false)}
          onSaved={(updated) => setProjects((current) => current.map((project) => project.id === updated.id ? updated : project))}
          onDeleted={(projectId) => {
            const remaining = projects.filter((project) => project.id !== projectId)
            setProjects(remaining)
            setDetailsOpen(false)
            void prefs.patch({ active_project_id: remaining[0]?.id ?? null })
          }}
        />
      )}
      {createProjectOpen && (
        <ProjectCreateOverlay
          agents={agents}
          onClose={() => setCreateProjectOpen(false)}
          onCreated={(project) => {
            setProjects((current) => [project, ...current])
            setCreateProjectOpen(false)
            void prefs.patch({ active_project_id: project.id })
          }}
        />
      )}
      {editingAgentId && (
        <ProjectAgentEditOverlay
          agentId={editingAgentId}
          onClose={() => setEditingAgentId(null)}
          onSaved={(updated) => setAgents((cur) => cur.map((agent) => agent.id === updated.id ? { ...agent, ...updated } : agent))}
        />
      )}
    </CockpitShell>
  )
}
