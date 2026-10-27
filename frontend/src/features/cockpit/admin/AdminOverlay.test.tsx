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
})
