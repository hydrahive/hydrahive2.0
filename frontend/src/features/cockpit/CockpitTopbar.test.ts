import { describe, expect, it } from "vitest"
import { readdirSync } from "node:fs"
import { join } from "node:path"
import { COCKPIT_HELP } from "./CockpitTopbar"

// Der Hilfe-Knopf der Cockpits muss den passenden Artikel öffnen (Befund 23.11.2026: Vault öffnete die Akte-Hilfe).
describe("Hilfe-Knopf der Cockpits", () => {
  it("Vault öffnet den Vault-Artikel", () => {
    expect(COCKPIT_HELP.vault).toBe("vault")
  })

  it("Kern-Cockpits zeigen auf vorhandene Kern-Artikel", () => {
    const dir = join(__dirname, "..", "..", "i18n", "help", "de")
    const core = new Set(readdirSync(dir).filter((f) => f.endsWith(".md")).map((f) => f.slice(0, -3)))
    for (const [cockpit, topic] of Object.entries(COCKPIT_HELP)) {
      if (cockpit === "media") continue                                  // Atelier = Modul-Hilfe
      expect(core.has(topic), `${cockpit} → ${topic}`).toBe(true)
    }
  })
})
