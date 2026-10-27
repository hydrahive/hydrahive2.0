// Task 0dda5420: Leer-Zustand mit der bunten Hydra (Stimmung statt Bildpfad).
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { EmptyState } from "./EmptyState"

describe("EmptyState", () => {
  it("Stimmung → Bild der bunten Hydra, Deko, mit Hinweis", () => {
    const html = renderToStaticMarkup(<EmptyState mood="sleeping" hint="Noch nichts da" />)
    expect(html).toContain('src="/hydra/sleeping.webp"')
    expect(html).toContain('alt=""')
    expect(html).toContain("Noch nichts da")
    expect(html).not.toContain("rgba(34,211,238")
  })
  it("Größe übernimmt der Aufrufer", () => {
    expect(renderToStaticMarkup(<EmptyState mood="confused" size={180} />)).toContain('width="180"')
  })
})

// Module (z. B. patientenakte) rufen EmptyState noch mit eigenem Bild auf – darf nicht brechen.
describe("EmptyState – Verträglichkeit mit Modulen", () => {
  it("eigenes Bild über src bleibt möglich", () => {
    expect(renderToStaticMarkup(<EmptyState src="/illustrations/empty-akte.png" hint="x" />)).toContain('src="/illustrations/empty-akte.png"')
  })
  it("ohne mood und src: bunte Hydra „idle“", () => {
    expect(renderToStaticMarkup(<EmptyState hint="x" />)).toContain('src="/hydra/idle.webp"')
  })
})
