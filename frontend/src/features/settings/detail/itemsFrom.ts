import type { Agent } from "@/features/agents/types"
import type { Project } from "@/features/projects/types"
import type { PickerItem } from "../pickerFilter"

const TYPE_ORDER: Record<string, number> = { master: 0, project: 1, specialist: 2 }
const TYPE_LABEL: Record<string, string> = { master: "Master", project: "Projekt-Agent", specialist: "Spezialist" }
const PROJECT_STATUS: Record<string, string> = { paused: "pausiert", archived: "archiviert" }
const STATUS_ORDER: Record<string, number> = { active: 0, paused: 1, archived: 2 }

/** Agenten fürs Auswahlfeld: Master → Projekt-Agent → Spezialist, dann Name. */
export function agentItems(agents: Agent[]): PickerItem[] {
  return [...agents]
    .sort((a, b) => (TYPE_ORDER[a.type] ?? 9) - (TYPE_ORDER[b.type] ?? 9) || a.name.localeCompare(b.name))
    .map((a) => {
      const off = a.status !== "active"
      const parts = [TYPE_LABEL[a.type] ?? a.type, a.llm_model, ...(off ? ["aus"] : [])]
      return { id: a.id, name: a.name, detail: parts.filter(Boolean).join(" · "), dim: off }
    })
}

/** Projekte fürs Auswahlfeld: aktive → pausiert → archiviert, je nach Name; nicht aktive gedimmt. */
export function projectItems(projects: Project[]): PickerItem[] {
  return [...projects]
    .sort((a, b) => (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9) || a.name.localeCompare(b.name))
    .map((p) => ({ id: p.id, name: p.name, detail: PROJECT_STATUS[p.status], dim: p.status !== "active" }))
}
