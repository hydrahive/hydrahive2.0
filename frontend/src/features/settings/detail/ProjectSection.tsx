import { useCallback, useEffect, useMemo, useState } from "react"
import { projectsApi } from "@/features/projects/api"
import { NewProjectDialog } from "@/features/projects/NewProjectDialog"
import type { Project } from "@/features/projects/types"
import { ItemPicker } from "../ItemPicker"
import { ProjectSettings } from "./ProjectSettings"
import { projectItems } from "./itemsFrom"
import { useSelectedItem } from "./useSelectedItem"

/** Reiter „Projekte“: Auswahlfeld mit Suche oben, Einstellungen des gewählten Projekts darunter. */
export function ProjectSection() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)

  const load = useCallback(() => {
    projectsApi.list().then(setProjects).catch(() => setProjects([])).finally(() => setLoading(false))
  }, [])
  useEffect(() => { load() }, [load])

  const items = useMemo(() => projectItems(projects), [projects])
  const { value, select } = useSelectedItem(items, loading)

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 border-b border-[#2a364b] px-4 py-2.5">
        <ItemPicker label="Projekt" items={items} value={value} onChange={select} onCreate={() => setCreating(true)} />
      </div>
      <div className="min-h-0 flex-1">
        <ProjectSettings itemId={value} />
      </div>
      {creating && (
        <NewProjectDialog
          onClose={() => setCreating(false)}
          onCreated={(id) => { setCreating(false); load(); select(id) }}
        />
      )}
    </div>
  )
}
