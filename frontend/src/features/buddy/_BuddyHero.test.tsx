// Task 0dda5420, Etappe Buddy: „Aktiver Buddy“-Karte mit Tills Schreibtisch-Hydra und den fünf Köpfen als Tags.
import { renderToStaticMarkup } from "react-dom/server"
import { existsSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"
import { BuddyHero } from "./_BuddyHero"
import { HEAD_TAGS } from "./_buddyHeads"

const PUBLIC = join(__dirname, "../../../public")

describe("BuddyHero", () => {
  const html = renderToStaticMarkup(<BuddyHero agentName="till's Buddy" />)
  it("Hintergrund ist Tills Hydra am Schreibtisch, Name bleibt lesbar darüber", () => {
    expect(html).toContain('src="/hydra/schreibtisch.webp"')
    expect(html).toContain("till&#x27;s Buddy")
    expect(html).toContain("Aktiver Buddy")
    expect(existsSync(join(PUBLIC, "hydra/schreibtisch.webp"))).toBe(true)
  })
  it("fünf Köpfe als kleine Tags mit Namen (Professor, Denker, Macher, Träumer, Buddy)", () => {
    expect(HEAD_TAGS.map((h) => h.name)).toEqual(["Professor", "Denker", "Macher", "Träumer", "Buddy"])
    for (const h of HEAD_TAGS) {
      expect(html).toContain(`src="${h.src}"`)
      expect(html).toContain(`title="${h.name}"`)
      expect(existsSync(join(PUBLIC, h.src)), h.src).toBe(true)
    }
  })
  it("Bilder sind Deko (leerer Alternativtext) und werden spät geladen", () => {
    const imgs = [...html.matchAll(/<img[^>]*>/g)].map((m) => m[0])
    expect(imgs.length).toBe(6)
    expect(imgs.every((i) => i.includes('alt=""') && i.includes('loading="lazy"'))).toBe(true)
  })
})

// Klein neben jeder Buddy-Antwort ist die ganze Hydra kaum zu erkennen → der Buddy-Kopf (mint) als Avatar.
import { BuddyAvatar } from "./_BuddyAvatar"
describe("BuddyAvatar", () => {
  it("ruhend: Buddy-Kopf, kein Pulsieren", () => {
    const h = renderToStaticMarkup(<BuddyAvatar live={false} />)
    expect(h).toContain('src="/startdesk/koepfe/kopf-1-mint.webp"')
    expect(h).not.toContain("animate-pulse")
  })
  it("während Buddy antwortet: der Kopf pulsiert", () => {
    expect(renderToStaticMarkup(<BuddyAvatar live />)).toContain("animate-pulse")
  })
})
