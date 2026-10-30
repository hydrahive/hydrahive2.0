// Plan docs/plans/admin-reiter-archiv.md, Task 2: Reiter-Baustein für Admin-Fenster.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { AdminTabs } from "./AdminTabs"

const TABS = [
  { id: "speicher", label: "Speicher" },
  { id: "vorgaenge", label: "Vorgänge", dot: true },
  { id: "inhalt", label: "Inhalt", count: 12 },
] as const

const html = (aktiv = "speicher") => renderToStaticMarkup(
  <AdminTabs label="Archiv" idPrefix="archiv" tabs={TABS} active={aktiv} onSelect={() => {}}>
    <p>Inhalt des Reiters</p>
  </AdminTabs>,
)

describe("AdminTabs", () => {
  it("Rollen: Reiterleiste, Reiter, Inhaltsbereich", () => {
    const out = html()
    expect(out).toContain('role="tablist"')
    expect(out).toContain('aria-label="Archiv"')
    expect(out.match(/role="tab"/g)).toHaveLength(3)
    expect(out).toMatch(/role="tabpanel"[^>]*aria-labelledby="archiv-tab-speicher"/)
    expect(out).toContain("Inhalt des Reiters")
  })

  it("nur der aktive Reiter ist ausgewählt und per Tab erreichbar", () => {
    const out = html("inhalt")
    expect(out.match(/aria-selected="true"/g)).toHaveLength(1)
    expect(out).toMatch(/id="archiv-tab-inhalt"[^>]*aria-selected="true"[^>]*tabindex="0"/)
    expect(out).toMatch(/id="archiv-tab-speicher"[^>]*aria-selected="false"[^>]*tabindex="-1"/)
  })

  it("Zähler und Punkt (Punkt mit Text für Bildschirmleser)", () => {
    const out = html()
    expect(out).toMatch(/Inhalt<\/span><span[^>]*>12<\/span>/)
    expect(out).toContain('data-tab-dot="vorgaenge"')
    expect(out).toMatch(/sr-only[^>]*>[^<]+</)
  })
})
