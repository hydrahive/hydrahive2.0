import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), post: vi.fn() } }))
import { OrphansView } from "./OrphansSection"
import { cleanupSelection, type OrphanScan } from "./api"

const SCAN: OrphanScan = {
  complete: true,
  workspaces: [
    { id: "a1", kind: "specialists", size: 0, files: 0, empty: true, complete: true },
    { id: "a2", kind: "master", size: 2051, files: 1, empty: true, complete: true },
    { id: "a3", kind: "specialists", size: 3 * 1024 ** 2, files: 12, empty: false, complete: true },
  ],
  agents: [{ id: "g1", name: "Helfer", project_id: "weg", type: "specialist" }],
}
const html = (scan: OrphanScan | null, busy = false) =>
  renderToStaticMarkup(<OrphansView scan={scan} busy={busy} onCleanup={() => {}} />).replace(/&quot;/g, '"')

describe("Bereich Waisen", () => {
  it("zählt leere, mit Inhalt (Größe) und Agenten ohne Projekt", () => {
    const out = html(SCAN)
    expect(out).toContain('data-archive-section="orphans"')
    expect(out).toContain('data-orphans-empty="2"')
    expect(out).toContain('data-orphans-full="1"')
    expect(out).toContain('data-orphans-agents="1"')
    expect(out).toContain("3.0 MB")
  })

  it("Knopf nur frei, wenn es etwas gibt und nichts läuft", () => {
    const btn = (o: string) => o.match(/<button[^>]*data-orphans-action="cleanup"[^>]*>/)?.[0] ?? ""
    expect(btn(html(SCAN))).not.toMatch(/\sdisabled=""/)
    expect(btn(html(SCAN, true))).toMatch(/\sdisabled=""/)
    expect(html({ complete: true, workspaces: [], agents: [] })).toContain("orphans.none")
  })

  it("unvollständig gezählt → „mindestens“", () => {
    expect(html({ ...SCAN, complete: false })).toContain("orphans.at_least")
  })

  it("räumt genau die angezeigten IDs auf", () => {
    expect(cleanupSelection(SCAN)).toEqual({ workspaces: ["a1", "a2", "a3"], agents: ["g1"] })
  })
})
