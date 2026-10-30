// Plan docs/plans/hydra-box-koepfe.md, Task 3: Admin-Fenster mit Thema bekommen Kopf + Verlauf.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/shared/dialog/useDialogFokus", () => ({ useDialogFokus: () => ({ current: null }) }))
import { AdminOverlay } from "./AdminOverlay"

const noop = () => {}

describe("AdminOverlay", () => {
  it("ohne Thema: kein Bild, Titel und Schließen da", () => {
    const html = renderToStaticMarkup(<AdminOverlay title="Module" onClose={noop}><p>x</p></AdminOverlay>)
    expect(html).not.toContain("<img")
    expect(html).toContain('aria-label="Schließen"')
  })
  it("mit Thema: Kopfbild vor dem Titel, Verlauf in der Kopfleiste", () => {
    const html = renderToStaticMarkup(<AdminOverlay title="KI-Modelle" eyebrow="Admin" theme="ideen" onClose={noop}><p>x</p></AdminOverlay>)
    expect(html).toMatch(/<header[^>]*data-box-theme="ideen"[\s\S]*<img[^>]*kopf-2-lila[\s\S]*KI-Modelle/)
    expect(html).toContain('aria-label="Schließen"')
  })
  // Plan farbstufen-kopffarben, Task 3
  it("Fenster aus Stufen: Fläche box, Kopf kopf, Fuß tief, Streifen in Kopffarbe", () => {
    const html = renderToStaticMarkup(<AdminOverlay title="KI" theme="ideen" footer={<b>f</b>} onClose={noop}><p>x</p></AdminOverlay>)
    expect(html).toMatch(/role="dialog"[^>]*bg-s-box/)
    expect(html).toMatch(/<header[^>]*bg-s-kopf/)
    expect(html).toMatch(/<footer[^>]*bg-s-tief/)
    expect(html).toMatch(/border-left-color:\s*#a78bfa/)
    expect(html).not.toMatch(/#0e1420|#131b2a|#0b111c|#2a364b|bg-gradient/)
  })
  it("Zustand im Fenster: Schild im Kopf", () => {
    const html = renderToStaticMarkup(<AdminOverlay title="Module" theme="werkzeug" status="warnung" onClose={noop}><p>x</p></AdminOverlay>)
    expect(html).toMatch(/<header[\s\S]*data-box-status="warnung"[\s\S]*<\/header>/)
  })
})
