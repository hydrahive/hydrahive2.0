// Plan docs/plans/hydra-box-koepfe.md, Task 3: Boxen mit Thema bekommen Kopf + Verlauf.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { CockpitPanel } from "./CockpitPanel"

describe("CockpitPanel", () => {
  it("ohne Thema: unverändert, kein Bild", () => {
    const html = renderToStaticMarkup(<CockpitPanel title="Status" eyebrow="Admin"><p>x</p></CockpitPanel>)
    expect(html).not.toContain("<img")
    expect(html).toContain("Status")
  })
  it("mit Thema: Kopfbild vor dem Titel, Verlauf in der Themenfarbe", () => {
    const html = renderToStaticMarkup(<CockpitPanel title="Werkzeuge" eyebrow="Kompakt" theme="werkzeug"><p>x</p></CockpitPanel>)
    expect(html).toMatch(/<img[^>]*kopf-3-orange[\s\S]*Werkzeuge/)
    expect(html).toContain("data-box-theme=\"werkzeug\"")
    expect(html).not.toMatch(/bg-gradient-to-b/)
  })
  it("mit Thema aber ohne Titel: trotzdem Kopf (z. B. reine Inhaltsbox)", () => {
    expect(renderToStaticMarkup(<CockpitPanel theme="status"><p>x</p></CockpitPanel>)).toContain("kopf-4-tuerkis")
  })

  // Plan docs/plans/farbstufen-kopffarben.md, Task 3: Stufen + Kopffarbe + Zustand.
  it("Fläche und Rand kommen aus den Stufen, keine festen Werte", () => {
    const html = renderToStaticMarkup(<CockpitPanel title="Status"><p>x</p></CockpitPanel>)
    expect(html).toContain("bg-s-box")
    expect(html).toContain("border-s-rand")
    expect(html).not.toMatch(/#151c2b|#2a364b/)
  })
  it("Kopfzeile ist abgesetzt (eigene Stufe + Trennlinie)", () => {
    const html = renderToStaticMarkup(<CockpitPanel title="Status" theme="status"><p>x</p></CockpitPanel>)
    const kopf = html.match(/<header[^>]*>/)?.[0] ?? ""
    expect(kopf).toContain("bg-s-kopf")
    expect(kopf).toContain("border-b ")
  })
  it("mit Thema: Streifen links in der Kopffarbe", () => {
    const html = renderToStaticMarkup(<CockpitPanel title="W" theme="werkzeug"><p>x</p></CockpitPanel>)
    expect(html).toMatch(/border-left-color:\s*#f97316/)
    expect(html).toMatch(/border-left-width:\s*4px/)
  })
  it("Zustand Fehler: roter Streifen + Schild mit Wort, Kopffarbe wird übermalt", () => {
    const html = renderToStaticMarkup(<CockpitPanel title="Sicherung" theme="wissen" status="fehler"><p>x</p></CockpitPanel>)
    expect(html).toMatch(/border-left-color:\s*#fb7185/)
    expect(html).toContain('data-box-status="fehler"')
  })
  it("ohne Thema und Zustand: kein Streifen, kein Schild", () => {
    const html = renderToStaticMarkup(<CockpitPanel title="Status"><p>x</p></CockpitPanel>)
    expect(html).not.toContain("border-left-color")
    expect(html).not.toContain("data-box-status")
  })
})
