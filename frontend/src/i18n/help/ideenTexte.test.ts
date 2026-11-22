// Das Modul scratchpad heißt seit 2.0.0 „Ideen“ (hydrahive2-modules#368): einzelne Ideen statt eines freien Zettels.
// Adresse und Hilfe-Thema bleiben "scratchpad"; die Texte im Kern dürfen den alten Zettel nicht mehr beschreiben.
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"
import { buddyOfflineActions } from "@/features/cockpit/actionRegistry"

const SRC = join(__dirname, "..", "..")
const read = (...parts: string[]) => readFileSync(join(SRC, ...parts), "utf8")
const topics = (lang: string) =>
  (JSON.parse(read("i18n", "locales", lang, "help.json")) as { manual: { topics: Record<string, string> } }).manual.topics

describe("Handbuch-Eintrag zum Modul Ideen", () => {
  // Der Artikel selbst liegt seit der Umstellung im Modul (scratchpad/frontend/help/de/scratchpad.md, Modul-Repo).
  it("heißt im Handbuch Ideen / Ideas", () => {
    expect(topics("de").scratchpad).toBe("Ideen")
    expect(topics("en").scratchpad).toBe("Ideas")
  })
})

describe("Verknüpfungen zum Modul Ideen", () => {
  it("„Idee merken“ führt weiter nach /scratchpad und nennt den alten Namen nicht", () => {
    const action = buddyOfflineActions.find((item) => item.id === "remember")
    expect(action?.path).toBe("/scratchpad")
    expect(action?.label).toBe("Idee merken")
    expect(action?.description).not.toMatch(/scratchpad/i)
  })

  it("die Buddy-Seite beschriftet die Verknüpfung mit Ideen", () => {
    const source = read("features", "buddy", "BuddyPage.tsx")
    expect(source).toContain('["Ideen", "/scratchpad"]')
    expect(source).not.toContain('"Scratchpad"')
  })
})
