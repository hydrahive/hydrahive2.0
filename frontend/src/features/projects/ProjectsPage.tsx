import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import { NewProjectDialog } from "./NewProjectDialog"
import { ProjectForm } from "./ProjectForm"
import { ProjectList } from "./ProjectList"
import { CollapsibleSidebar } from "@/shared/CollapsibleSidebar"
import type { Project } from "./types"

export function ProjectsPage() {
  const { t } = useTranslation("projects")
  const [projects, setProjects] = useState<Project[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [showNew, setShowNew] = useState(false)

  async function loadProjects(selectId?: string) {
    const list = await projectsApi.list()
    setProjects(list)
    if (selectId) setActiveId(selectId)
    else if (!activeId && list.length > 0) setActiveId(list[0].id)
  }

  useEffect(() => { loadProjects().catch(() => {}) }, [])

  function handleSaved(updated: Project) {
    setProjects((cur) => cur.map((p) => (p.id === updated.id ? updated : p)))
  }

  function handleDeleted() {
    if (!activeId) return
    setProjects((cur) => cur.filter((p) => p.id !== activeId))
    setActiveId(null)
  }

  function handleCreated(id: string) {
    setShowNew(false)
    loadProjects(id)
  }

  const active = projects.find((p) => p.id === activeId) ?? null

  return (
    <div className="flex h-[calc(100dvh-3rem)] -m-4 md:-m-6">
      <main className="flex-1 min-w-0">
        {active ? (
          <ProjectForm key={active.id} project={active} onSaved={handleSaved} onDeleted={handleDeleted} />
        ) : (
          <div className="flex items-center justify-center h-full text-sm text-zinc-600">
            {t("select_or_new")}
          </div>
        )}
      </main>

      <CollapsibleSidebar>
        <ProjectList
          projects={projects} activeId={activeId}
          onSelect={setActiveId} onNew={() => setShowNew(true)}
        />
      </CollapsibleSidebar>

      {showNew && (
        <NewProjectDialog onClose={() => setShowNew(false)} onCreated={handleCreated} />
      )}
    </div>
  )
}
