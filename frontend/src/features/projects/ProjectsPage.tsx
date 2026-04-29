import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import { NewProjectDialog } from "./NewProjectDialog"
import { ProjectForm } from "./ProjectForm"
import { ProjectList } from "./ProjectList"
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
    <div className="flex h-[calc(100vh-3.5rem)] -m-6">
      <main className="flex-1 min-w-0">
        {active ? (
          <ProjectForm key={active.id} project={active} onSaved={handleSaved} onDeleted={handleDeleted} />
        ) : (
          <div className="flex items-center justify-center h-full text-sm text-zinc-600">
            {t("select_or_new")}
          </div>
        )}
      </main>

      <aside className="w-72 border-l border-white/[6%] bg-white/[2%] flex-shrink-0">
        <ProjectList
          projects={projects} activeId={activeId}
          onSelect={setActiveId} onNew={() => setShowNew(true)}
        />
      </aside>

      {showNew && (
        <NewProjectDialog onClose={() => setShowNew(false)} onCreated={handleCreated} />
      )}
    </div>
  )
}
