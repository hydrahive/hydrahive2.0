// Task 0dda5420: Die Schritte im Medien-Cockpit zeigen Hydra-Bildchen statt reiner Linien-Symbole.
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"
import { TILE_ART, tileArt } from "@/shared/brand/tileArt"

describe("Medien-Cockpit-Kacheln", () => {
  it("jeder bekannte Schritt und der Videoschnitt hat ein Bildchen", () => {
    for (const k of ["media:characters", "media:generate", "media:gallery", "media:clips", "media:film", "media:editor"]) {
      expect(TILE_ART[k], k).toMatch(/^\/kacheln\/media-[a-z]+\.webp$/)
    }
  })
  it("unbekannter Modul-Schritt bleibt beim Symbol", () => {
    expect(tileArt("media:irgendwas")).toBeNull()
  })
  it("MediaCockpitPage zeichnet die Schritte mit TileIcon", () => {
    const src = readFileSync(join(__dirname, "MediaCockpitPage.tsx"), "utf8")
    expect(src).toMatch(/<TileIcon[^>]*target=\{`media:\$\{/)
    expect(src).toMatch(/<TileIcon[^>]*target="media:editor"/)
  })
})
