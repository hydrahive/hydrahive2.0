import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { projectsApi } from "@/features/projects/api"
import { ProjectFormTabs } from "./ProjectFormTabs"
import type { Project } from "@/features/projects/types"

/**
 * Projekt-Einstellungen für den Settings-Hub. Submenü rechts wählt das Projekt,
 * hier werden dessen Settings als Karteikarten gezeigt (ohne Auswertungs-Tabs).
 */
export function ProjectSettings({ itemId }: { itemId: string | null }) {
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!itemId) { setProject(null); return }
    setLoading(true)
    projectsApi.get(itemId)
      .then(setProject)
      .catch(() => setProject(null))
      .finally(() => setLoading(false))
  }, [itemId])

  if (!itemId) {
    return (
      <p className="py-16 text-center text-sm text-zinc-500">
        Rechts ein Projekt wählen, um seine Einstellungen zu bearbeiten.
      </p>
    )
  }
  if (loading || !project) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Loader2 size={20} className="animate-spin text-zinc-500" />
      </div>
    )
  }

  return (
    <ProjectFormTabs
      key={project.id}
      project={project}
      onSaved={setProject}
      onDeleted={() => setProject(null)}
    />
  )
}
