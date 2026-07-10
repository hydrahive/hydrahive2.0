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
import { ProjectAiSettingsPanel } from "./project/ProjectAiSettingsPanel"
import { ProjectGitSummary } from "./project/ProjectGitSummary"
import { ProjectGitTreePanel } from "./project/ProjectGitTreePanel"
import { ProjectWorkspacePanel } from "./project/ProjectWorkspacePanel"
import { ProjectSelector } from "./project/ProjectSelector"
import { ProjectTasksPanel } from "./project/ProjectTasksPanel"

export function ProjectCockpitPage() {
  const prefs = useUserPreferences()
  const [projects, setProjects] = useState<Project[]>([])
  const [agents, setAgents] = useState<AgentBrief[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [wsFile, setWsFile] = useState<{ path: string; kind: FileKind } | null>(null)
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
  const selectedAgentModel = agents.find((agent) => agent.id === selectedAgentId)?.llm_model ?? ""

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
      className="flex h-[100dvh] min-h-0 flex-col overflow-hidden bg-[#080b11]"
      hideHeader
    >
      <header className="flex h-[58px] shrink-0 items-center gap-[18px] border-b border-[#2a364b] bg-gradient-to-b from-[#131b2a] to-[#0e1420] px-[18px]">
        <div className="font-black tracking-[-0.03em] text-[#e8eef8]">HydraHive</div>
        <nav className="flex gap-1.5 text-sm">
          <span className="rounded-[4px] bg-[#1c2940] px-3 py-2 font-semibold text-[#69d7ff]">Projekte</span>
          <span className="rounded-[4px] px-3 py-2 text-[#8d9ab0]">Buddy</span>
          <span className="rounded-[4px] px-3 py-2 text-[#8d9ab0]">Media</span>
          <span className="rounded-[4px] px-3 py-2 text-[#8d9ab0]">Vault</span>
          <span className="rounded-[4px] px-3 py-2 text-[#8d9ab0]">Admin</span>
        </nav>
        <div className="flex-1" />
        {activeProject && <div className="hidden text-xs text-[#8d9ab0] lg:block">Projekt bleibt gespeichert: {activeProject.name}</div>}
        <CockpitButton onClick={() => window.open("/settings/projects", "_self")}>Projekt-Einstellungen</CockpitButton>
      </header>
      {error && <div className="mx-[10px] mt-[10px] shrink-0 rounded-[4px] border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{error}</div>}
      <div className="grid min-h-0 flex-1 gap-[10px] overflow-hidden p-[10px] xl:grid-cols-[270px_minmax(420px,1fr)_360px]">
        <aside className="min-h-0 space-y-[10px] overflow-y-auto pr-1">
          <CockpitPanel>
            <ProjectSelector projects={projects} activeProjectId={activeProjectId} loading={loading || prefs.loading} onPick={pickProject} />
            {activeProject && <p className="mt-3 line-clamp-3 text-xs text-zinc-500">{activeProject.description || "Keine Beschreibung."}</p>}
          </CockpitPanel>
          <ProjectAgentsPanel
            agents={agents}
            projectAgentId={projectAgentId}
            selectedAgentId={selectedAgentId}
            onSelect={(agentId) => {
              if (!activeProjectId) return
              setSelectedAgentByProject((cur) => ({ ...cur, [activeProjectId]: agentId }))
            }}
          />
          <ProjectGitSummary projectId={activeProjectId} />
          <ProjectAiSettingsPanel
            agentId={projectAgentId}
            agents={agents}
            onAgentChanged={(updated) => setAgents((cur) => cur.map((agent) => agent.id === updated.id ? { ...agent, ...updated } : agent))}
          />
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
    </CockpitShell>
  )
}
