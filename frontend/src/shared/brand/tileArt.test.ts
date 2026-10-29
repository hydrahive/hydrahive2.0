// Task 0dda5420, Stufe 2: eigene Hydra-Bildchen für Kacheln mit eigenem Ziel.
import { existsSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"
import { TILE_ART, tileArt } from "./tileArt"

const PUBLIC = join(__dirname, "../../../public")

describe("TILE_ART", () => {
  it("jedes Bildchen liegt wirklich in public/kacheln/", () => {
    for (const [k, src] of Object.entries(TILE_ART)) expect(existsSync(join(PUBLIC, src)), k).toBe(true)
  })
  it("deckt alle Ziele von Admin-Cockpit und Buddy ab", () => {
    for (const k of ["/system", "/users", "/modules", "/extensions", "/plugins", "/credentials", "/archive",
      "/llm", "/mcp", "/skills", "/vms", "/containers", "/nodes", "/jobs", "/scheduled-tasks",
      "/federation", "/zahnfee-config", "/system/settings", "/access", "/projects", "/media", "/vault", "/admin",
      "/scratchpad", "/minigames", "/boardgames", "buddy:today", "buddy:remember", "buddy:project", "gitea", "backup"]) {
      expect(TILE_ART[k], k).toMatch(/^\/kacheln\/[a-z-]+\.webp$/)
    }
  })
  it("unbekanntes Ziel: kein Bild (Kachel bleibt beim Symbol)", () => {
    expect(tileArt("/gibtsnicht")).toBeNull()
    expect(tileArt("toString")).toBeNull()
  })
})
