import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

// Task 08c5c546 (docs/specs/modul-ladeschleife.md): Werkstatt blieb schwarz.
// Lade-Schleife index.generated → legal → ChatPane → WorkspacePanel: Beim Laden
// sind die Modul-Listen noch nicht gesetzt, erst später. Der Mock bildet genau
// das nach — die Werte kommen per Getter erst NACH dem Import der Kern-Datei.
const mods = vi.hoisted(() => ({ value: {} as Record<string, unknown> }))
vi.mock("@/modules/index.generated", () => {
  const names = ["moduleRoutes", "moduleNav", "moduleNavOwners", "moduleI18n", "moduleBuddyWidgets",
    "moduleBuddyMediaWidgets", "moduleWorkspaceTabs", "moduleSlotBlocks", "moduleMediaSources", "moduleMediaWorkflows"]
  const api: Record<string, unknown> = {}
  for (const n of names) Object.defineProperty(api, n, { enumerable: true, get: () => mods.value[n] })
  return api
})
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), post: vi.fn() }, buildErrorMessage: vi.fn() }))

import { moduleList } from "./moduleList"
import { WorkspacePanel } from "@/features/chat/workspace/WorkspacePanel"
import { mediaWorkflows, mediaSources, primaryMediaWorkflow } from "@/features/cockpit/media/mediaRegistry"
import { buddyMediaWidgets } from "@/features/buddy/moduleMediaWidgets"

function Tab() { return <div>tab-inhalt</div> }

describe("moduleList", () => {
  it("gibt [] für noch nicht gesetzte Werte", () => {
    expect(moduleList(undefined)).toEqual([])
    expect(moduleList(null)).toEqual([])
    expect(moduleList("x")).toEqual([])
  })
  it("gibt ein Array unverändert zurück", () => {
    const a = [1, 2]
    expect(moduleList(a)).toBe(a)
  })
})

describe("Modul-Listen werden erst beim Gebrauch gelesen", () => {
  it("WorkspacePanel: Modul-Reiter, der erst nach dem Laden gesetzt wird, erscheint", () => {
    mods.value = { moduleWorkspaceTabs: [{ id: "tasks", label: "Aufgaben-Reiter", component: Tab }] }
    const html = renderToStaticMarkup(<WorkspacePanel agentId="a1" onOpenFile={() => {}} />)
    expect(html).toContain("Aufgaben-Reiter")
  })

  it("WorkspacePanel: noch kein Modul-Wert → kein Absturz, Kern-Reiter bleiben", () => {
    mods.value = {}
    const html = renderToStaticMarkup(<WorkspacePanel agentId="a1" onOpenFile={() => {}} />)
    expect(html).toContain("tab_files")
    expect(html).toContain("tab_git")
  })

  it("Media: Workflows und Quellen kommen beim Aufruf", () => {
    const wf = { id: "atelier", steps: [], component: Tab }
    const src = { id: "s", resolveRoot: vi.fn(), loadItems: vi.fn() }
    mods.value = { moduleMediaWorkflows: [wf], moduleMediaSources: [src] }
    expect(mediaWorkflows()).toEqual([wf])
    expect(mediaSources()).toEqual([src])
    expect(primaryMediaWorkflow()).toBe(wf)
    mods.value = {}
    expect(mediaWorkflows()).toEqual([])
    expect(primaryMediaWorkflow()).toBeNull()
  })

  it("Buddy: Medien-Kacheln kommen beim Aufruf", () => {
    mods.value = { moduleBuddyMediaWidgets: [{ id: "radio", order: 1, component: Tab }] }
    expect(buddyMediaWidgets().map((w) => w.id)).toEqual(["radio"])
    mods.value = {}
    expect(buddyMediaWidgets()).toEqual([])
  })
})
