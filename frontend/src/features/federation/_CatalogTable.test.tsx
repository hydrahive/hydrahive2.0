// Katalog-Reiter auf Clients (docs/specs/federation-shared-tasks.md §Oberfläche Cockpit):
// Tabelle, Leerzustand, „Mehr laden“.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
import { CatalogTable } from "./_CatalogTable"
import type { CatalogMirrorItem } from "./types"

const item = (over: Partial<CatalogMirrorItem> = {}): CatalogMirrorItem => ({
  origin_fp: "fp1", origin_name: "hydrahome", kind: "task", item_id: "abc12345", short_id: "abc12345",
  owner: "till", title: "Etwas erledigen", status: "open", priority: "normal",
  project_id: "p1", project_name: "Hydrahive DEV",
  created_at: "2026-11-20T10:00:00.000+00:00", updated_at: "2026-11-21T10:00:00.000+00:00",
  received_at: "2026-11-21T10:01:00.000+00:00", ...over,
})

const render = (p: Partial<React.ComponentProps<typeof CatalogTable>> = {}) =>
  renderToStaticMarkup(
    <CatalogTable items={[]} loading={false} loadingMore={false} hasMore={false} onLoadMore={() => {}} {...p} />,
  )

describe("Leerzustand", () => {
  it("ohne Einträge: Hinweis, keine Tabelle", () => {
    const h = render()
    expect(h).toContain("catalog_tab.empty")
    expect(h).not.toContain("<table")
  })
  it("während des Ladens: nur Ladehinweis", () => {
    const h = render({ loading: true })
    expect(h).toContain("loading")
    expect(h).not.toContain("catalog_tab.empty")
    expect(h).not.toContain("<table")
  })
})

describe("Liste rendert", () => {
  it("zeigt Art, Kurz-ID, Titel, Status, Projekt, Instanz, geändert am", () => {
    const h = render({ items: [item()] })
    expect(h).toContain("<table")
    expect(h).toContain("catalog_tab.kind_task")
    expect(h).toContain("abc12345")
    expect(h).toContain("Etwas erledigen")
    expect(h).toContain("catalog_tab.status.open")
    expect(h).toContain("Hydrahive DEV")
    expect(h).toContain("hydrahome")
  })
  it("Idee ohne Projekt: Platzhalter „—“", () => {
    const h = render({ items: [item({ kind: "idea", project_id: null, project_name: null, status: "new" })] })
    expect(h).toContain("catalog_tab.kind_idea")
    expect(h).toContain("catalog_tab.status.new")
    expect(h).toContain(">—<")
  })
})

describe("Mehr laden", () => {
  it("ohne has_more: kein Knopf", () => {
    expect(render({ items: [item()], hasMore: false })).not.toContain("catalog_tab.load_more")
  })
  it("mit has_more: Knopf sichtbar und bedienbar", () => {
    const h = render({ items: [item()], hasMore: true })
    expect(h).toMatch(/<button[^>]*>catalog_tab\.load_more<\/button>/)
  })
  it("während des Nachladens: Knopf gesperrt mit anderem Text", () => {
    const h = render({ items: [item()], hasMore: true, loadingMore: true })
    expect(h).toMatch(/<button[^>]*disabled=""[^>]*>catalog_tab\.loading_more<\/button>/)
  })
})
