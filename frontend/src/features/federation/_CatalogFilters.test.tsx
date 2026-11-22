// Katalog-Reiter auf Clients (docs/specs/federation-shared-tasks.md §Oberfläche Cockpit): Filter.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
import { CatalogFilters } from "./_CatalogFilters"
import { EMPTY_FILTERS } from "./_catalogMirror"
import type { CatalogMirrorFacets } from "./types"

const facets: CatalogMirrorFacets = {
  instances: [{ origin_fp: "fp1", origin_name: "hydrahome", count: 3 }],
  projects: ["Hydrahive DEV"],
}

const render = (f = EMPTY_FILTERS, fa = facets) =>
  renderToStaticMarkup(<CatalogFilters filters={f} facets={fa} onChange={() => {}} />)

describe("Filter bauen die richtige Query (über die Darstellung geprüft)", () => {
  it("zeigt Instanzen und Projekte aus den facets", () => {
    const h = render()
    expect(h).toContain("hydrahome")
    expect(h).toContain("(3)")
    expect(h).toContain("Hydrahive DEV")
  })
  it("ohne facets: keine Filterblöcke für Instanz/Projekt", () => {
    const h = render(EMPTY_FILTERS, { instances: [], projects: [] })
    expect(h).not.toContain('data-part="instance-filter"')
    expect(h).not.toContain('data-part="project-filter"')
  })
  it("Status-Filter zeigt beide Arten, solange keine Art gewählt ist", () => {
    const h = render()
    expect(h).toContain("catalog_tab.status.open")
    expect(h).toContain("catalog_tab.status.new")
  })
  it("mit Art „task“: nur Task-Status", () => {
    const h = render({ ...EMPTY_FILTERS, kind: "task" })
    expect(h).toContain("catalog_tab.status.open")
    expect(h).not.toContain("catalog_tab.status.new")
  })
  it("ausgewählte Instanz/Projekt/Status sind als gedrückt markiert", () => {
    const h = render({ ...EMPTY_FILTERS, instances: ["fp1"], project: "Hydrahive DEV", statuses: ["open"] })
    expect(h).toMatch(/aria-pressed="true"[^>]*>hydrahome/)
    expect(h).toMatch(/aria-pressed="true"[^>]*>Hydrahive DEV/)
    expect(h).toContain('aria-pressed="true"')
  })
  it("Suchfeld übernimmt den aktuellen Text", () => {
    const h = render({ ...EMPTY_FILTERS, q: "foo" })
    expect(h).toContain('value="foo"')
  })
})
