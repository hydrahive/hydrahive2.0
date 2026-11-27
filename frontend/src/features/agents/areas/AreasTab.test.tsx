import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import { AreasView } from "./AreasTab"
import type { AreaCatalog, AreaStatus } from "./types"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: { count?: number }) => (o?.count !== undefined ? `${k}:${o.count}` : k) }) }))

const catalog: AreaCatalog = {
  groups: [{ id: "files_code", name: "Dateien & Code" }, { id: "internet", name: "Internet" }],
  areas: [
    { id: "files_read", group: "files_code", name: "Dateien lesen", sentence: "Dateien lesen", marks: [], tools: ["file_read"], source: "core" },
    { id: "web_search", group: "internet", name: "Im Internet suchen", sentence: "Suchen", marks: ["costly"], tools: ["web_search"], source: "core" },
  ],
  base: ["find_tools"], unassigned: [],
}
const status = (editable: boolean): AreaStatus => ({
  editable,
  areas: [
    { id: "files_read", state: "on", have: ["file_read"], missing: [], new: [], via_category: [] },
    { id: "web_search", state: "off", have: [], missing: ["web_search"], new: [], via_category: [] },
  ],
})
const base = { catalog, onToggle: () => {}, onAdopt: () => {}, mode: "classic" as const, onMode: () => {} }

describe("AreasView – AB3", () => {
  it("zeigt Gruppen-Überschriften in der Reihenfolge der Gruppen und je Bereich eine Zeile", () => {
    const html = renderToStaticMarkup(<AreasView {...base} status={status(true)} />)
    expect(html.indexOf("Dateien &amp; Code")).toBeGreaterThan(-1)
    expect(html.indexOf("Dateien &amp; Code")).toBeLessThan(html.indexOf("Internet"))
    expect(html).toContain("Dateien lesen"); expect(html).toContain("Im Internet suchen")
  })
  it("editable=false: Schalter gesperrt und Hinweis „Nur Admins“ sichtbar", () => {
    const html = renderToStaticMarkup(<AreasView {...base} status={status(false)} />)
    expect(html).toContain("areas.readonly")
    expect(html).toMatch(/role="switch"[^>]*disabled/)
  })
  it("editable=true: kein Hinweis, Schalter bedienbar", () => {
    const html = renderToStaticMarkup(<AreasView {...base} status={status(true)} />)
    expect(html).not.toContain("areas.readonly")
    expect(html).not.toMatch(/role="switch"[^>]*disabled/)
  })
  it("zeigt den Schalter „Werkzeuge bei Bedarf suchen“ und seinen Zustand", () => {
    const off = renderToStaticMarkup(<AreasView {...base} status={status(true)} />)
    expect(off).toContain("areas.catalog_mode"); expect(off).toContain('data-testid="catalog-mode-switch"')
    expect(off).toMatch(/data-testid="catalog-mode-switch"[^>]*aria-checked="false"/)
    const on = renderToStaticMarkup(<AreasView {...base} mode="catalog" status={status(true)} />)
    expect(on).toMatch(/data-testid="catalog-mode-switch"[^>]*aria-checked="true"/)
  })
  it("zeigt keine Tool-Namen in der Bereichsansicht", () => {
    const html = renderToStaticMarkup(<AreasView {...base} status={status(true)} />)
    expect(html).not.toContain("file_read"); expect(html).not.toContain("web_search\"")
  })
})
