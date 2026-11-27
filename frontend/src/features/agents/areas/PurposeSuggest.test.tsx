import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import { PurposeView, resolveSuggestions } from "./PurposeView"
import type { AreaCatalog, Suggestion } from "./types"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))

const catalog: AreaCatalog = {
  groups: [{ id: "g", name: "G" }],
  areas: [
    { id: "web_search", group: "g", name: "Im Internet suchen", sentence: "Suchmaschine befragen", marks: ["costly"], tools: ["web_search"], source: "core" },
    { id: "files_read", group: "g", name: "Dateien lesen", sentence: "Dateien lesen", marks: [], tools: ["file_read"], source: "core" },
  ],
  base: [], unassigned: [],
}
const props = { purpose: "", onPurpose: () => {}, onSuggest: () => {}, onToggle: () => {}, onApply: () => {}, busy: false, picked: [] as string[], error: null }

describe("resolveSuggestions – Security (Review #791)", () => {
  it("löst area gegen den Katalog auf, Name und Satz kommen von dort, nicht vom Modell", () => {
    const s: Suggestion[] = [{ area: "web_search", reason: "weil Recherche" }]
    const out = resolveSuggestions(s, catalog)
    expect(out).toHaveLength(1)
    expect(out[0].area.name).toBe("Im Internet suchen"); expect(out[0].reason).toBe("weil Recherche")
  })
  it("ignoriert unbekannte IDs still", () => {
    const out = resolveSuggestions([{ area: "gibt_es_nicht", reason: "x" }, { area: "files_read", reason: "y" }], catalog)
    expect(out.map((o) => o.area.id)).toEqual(["files_read"])
  })
  it("ignoriert Dubletten, kaputte Einträge und Nicht-Listen", () => {
    expect(resolveSuggestions([{ area: "files_read", reason: "a" }, { area: "files_read", reason: "b" }], catalog)).toHaveLength(1)
    expect(resolveSuggestions([null, 5, { reason: "ohne area" }, { area: 7 }] as never, catalog)).toEqual([])
    expect(resolveSuggestions(undefined as never, catalog)).toEqual([])
  })
  it("kürzt einen sehr langen Grund und macht aus Nicht-Text einen leeren Grund", () => {
    const long = resolveSuggestions([{ area: "files_read", reason: "x".repeat(900) }], catalog)[0].reason
    expect(long.length).toBeLessThanOrEqual(200)
    expect(resolveSuggestions([{ area: "files_read", reason: { evil: 1 } as never }], catalog)[0].reason).toBe("")
  })
})

describe("PurposeView", () => {
  const sug = resolveSuggestions([{ area: "web_search", reason: "<img src=x onerror=alert(1)>" }], catalog)
  it("rendert den Grund nur als Text, nie als HTML", () => {
    const html = renderToStaticMarkup(<PurposeView {...props} suggestions={sug} />)
    expect(html).toContain("&lt;img src=x onerror=alert(1)&gt;")
    expect(html).not.toContain("<img")
    expect(html).not.toContain("dangerouslySetInnerHTML")
  })
  it("Zweck-Feld mit maxLength 500, Knopf während des Requests gesperrt", () => {
    const idle = renderToStaticMarkup(<PurposeView {...props} purpose="Recherche" suggestions={[]} />)
    expect(idle).toContain('maxLength="500"'); expect(idle).not.toMatch(/data-testid="suggest-button"[^>]*\sdisabled=""/)
    const busy = renderToStaticMarkup(<PurposeView {...props} purpose="Recherche" busy suggestions={[]} />)
    expect(busy).toMatch(/data-testid="suggest-button"[^>]*\sdisabled=""/)
  })
  it("leerer Zweck sperrt den Knopf", () => {
    expect(renderToStaticMarkup(<PurposeView {...props} purpose="  " suggestions={[]} />)).toMatch(/data-testid="suggest-button"[^>]*\sdisabled=""/)
  })
  it("Vorschläge sind nur Vorauswahl: Häkchen und sichtbares Übernehmen, Hinweis dass erst Speichern gilt", () => {
    const html = renderToStaticMarkup(<PurposeView {...props} suggestions={sug} picked={["web_search"]} />)
    expect(html).toContain('type="checkbox"'); expect(html).toContain("areas.purpose_apply"); expect(html).toContain("areas.purpose_hint")
    expect(html).toContain("Im Internet suchen")
  })
  it("ohne Häkchen ist Übernehmen gesperrt", () => {
    expect(renderToStaticMarkup(<PurposeView {...props} suggestions={sug} picked={[]} />)).toMatch(/data-testid="apply-button"[^>]*\sdisabled=""/)
  })
  it("zeigt Fehler nur als übersetzten Text, nie Rohtext", () => {
    const html = renderToStaticMarkup(<PurposeView {...props} suggestions={[]} error="errors:llm_failed" />)
    expect(html).toContain('role="alert"')
  })
})
