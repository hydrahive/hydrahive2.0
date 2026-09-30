import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

// api-client zieht i18n → @/modules/index.generated, das gibt es nur nach der
// Modul-Installation, nicht in der CI (gleiches Vorgehen wie users/api.test.ts).
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() } }))
import { ProjectTaskDetails } from "./ProjectTaskDetails"
import { formatVersionTime, historyLabel } from "./_projectTasksApi"

// Task d61ae32b, Punkt 2: Das Projekt-Cockpit zeigte weder Beschreibung noch
// Verlauf. Die Werkstatt (tasks-Modul) hat „Verlauf (N)“ seit 1.1.0.
const render = (p: Partial<Parameters<typeof ProjectTaskDetails>[0]> = {}) =>
  renderToStaticMarkup(
    <ProjectTaskDetails taskId="t1" description="" historyCount={0} {...p} />,
  )

describe("ProjectTaskDetails", () => {
  it("zeigt nichts ohne Beschreibung und ohne Verlauf", () => {
    expect(render()).toBe("")
  })

  it("zeigt die Beschreibung sichtbar und gekürzt, voller Text im title", () => {
    const html = render({ description: "Erste Zeile\nZweite Zeile" })
    expect(html).toMatch(/<p (?![^>]*hidden)[^>]*line-clamp-2[^>]*>Erste Zeile/)
    expect(html).toContain('title="Erste Zeile\nZweite Zeile"')
  })

  it("zeigt den Verlauf-Knopf mit Anzahl, zugeklappt ohne Inhalt", () => {
    const html = render({ historyCount: 3 })
    expect(html).toContain("Verlauf (3)")
    expect(html).not.toContain("lädt")
  })

  it("kein Verlauf-Knopf bei 0 oder fehlender Anzahl", () => {
    expect(render({ description: "x", historyCount: 0 })).not.toContain("Verlauf")
    expect(render({ description: "x", historyCount: undefined })).not.toContain("Verlauf")
  })
})

describe("Hilfen", () => {
  it("historyLabel", () => {
    expect(historyLabel(1)).toBe("Verlauf (1)")
    expect(historyLabel(12)).toBe("Verlauf (12)")
  })

  it("formatVersionTime kürzt ISO auf Datum + Minuten", () => {
    expect(formatVersionTime("2026-09-30T13:35:00.123+00:00")).toBe("2026-09-30 13:35")
  })
})

describe("ProjectTasksPanel bindet die Details ein", () => {
  it("Panel-Quelle nutzt ProjectTaskDetails mit description und history_count", async () => {
    const src = (await import("./ProjectTasksPanel.tsx?raw")).default as string
    expect(src).toContain("<ProjectTaskDetails")
    expect(src).toContain("description={task.description}")
    expect(src).toContain("historyCount={task.history_count}")
  })
})
