// Neues Logo mit der bunten Hydra (Task 0dda5420, Etappe Logo): ein Baustein für Kopfzeile, Anmeldung usw.
import { renderToStaticMarkup } from "react-dom/server"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"
import { BRAND, HydraLogo } from "./HydraLogo"

const PUBLIC = join(__dirname, "../../../public")

describe("HydraLogo", () => {
  it("Schriftzug: breites Logo mit Alternativtext „HydraHive“", () => {
    const html = renderToStaticMarkup(<HydraLogo variant="wordmark" />)
    expect(html).toContain(`src="${BRAND.wordmark}"`)
    expect(html).toContain('alt="HydraHive"')
  })
  it("Emblem: quadratisch", () => {
    const html = renderToStaticMarkup(<HydraLogo variant="emblem" className="h-9 w-9" />)
    expect(html).toContain(`src="${BRAND.emblem}"`)
    expect(html).toContain("h-9 w-9")
  })
  it("responsive: Emblem auf schmalen, Schriftzug ab md", () => {
    const html = renderToStaticMarkup(<HydraLogo variant="responsive" />)
    expect(html).toMatch(new RegExp(`src="${BRAND.emblem}"[^>]*class="[^"]*md:hidden`))
    expect(html).toMatch(new RegExp(`src="${BRAND.wordmark}"[^>]*class="[^"]*hidden[^"]*md:block`))
    // beide Bilder einzeln beschriftet (Bildschirmleser, Bild lädt nicht)
    expect(html.match(/<img[^>]*alt="HydraHive"/g)).toHaveLength(2)
  })
  it("alle Logo-Dateien liegen wirklich in public/", () => {
    for (const p of Object.values(BRAND)) expect(() => readFileSync(join(PUBLIC, p))).not.toThrow()
  })
  it("index.html: Favicon ist das neue Emblem, Titel „HydraHive“", () => {
    const html = readFileSync(join(PUBLIC, "../index.html"), "utf8")
    expect(html).toContain('href="/favicon-32.png"')
    expect(html).toContain('href="/apple-touch-icon.png"')
    expect(html).not.toContain("favicon.svg")
    expect(html).toContain("<title>HydraHive</title>")
  })
})
