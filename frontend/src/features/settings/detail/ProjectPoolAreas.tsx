import { useTranslation } from "react-i18next"
import { PoolAreasEditor } from "@/features/agents/areas/PoolAreasEditor"

/** Projekt-Pool in Bereichssprache: schränkt ein, was Agenten im Projekt per Auftrag bekommen (leer = keine Einschränkung). */
export function ProjectPoolAreas({ projectId, canEdit }: { projectId: string; canEdit: boolean }) {
  const { t } = useTranslation("agents")
  return <PoolAreasEditor path={`/projects/${encodeURIComponent(projectId)}/tool-pool`} readOnly={!canEdit} emptyMeansOpen
    title={t("areas.project_title")} hint={t("areas.project_hint")} />
}
