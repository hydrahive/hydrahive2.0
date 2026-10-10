import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

// Till 10.10.: „Verknüpfte Projekte“ gab es im Cockpit nicht – nur in der alten Projektverwaltung, die vom Cockpit
// aus nicht erreichbar ist. Jetzt unter Verwalten → Zugriff (docs/specs/linked-projects.md).
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(async () => []), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() } }))
import { ProjectAccessOverlay } from "./ProjectAccessOverlay"
import type { Project } from "@/features/projects/types"

const project = { id: "vr", name: "HydraVR", members: [], created_by: "till", allowed_specialists: [], linked_projects: [] } as unknown as Project

describe("ProjectAccessOverlay", () => {
  it("zeigt den Abschnitt „Verknüpfte Projekte“ neben Mitgliedern und Spezialisten", () => {
    const html = renderToStaticMarkup(<ProjectAccessOverlay project={project} onClose={() => {}} onChanged={() => {}} />)
    expect(html).toContain("Projektmitglieder")
    expect(html).toContain("linked.title")
    expect(html).toContain("linked.hint")
  })
})
