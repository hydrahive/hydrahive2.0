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

describe("Hilfe-Artikel zum Modul Ideen", () => {
  it("beschreibt einzelne Ideen, nicht mehr den Zettel mit zwei Bereichen (de)", () => {
    const text = read("i18n", "help", "de", "scratchpad.md")
    expect(text.startsWith("# Ideen\n")).toBe(true)
    for (const word of ["Kopfzeile", "Beschreibung", "Projekt", "Status", "Anmerkung"]) expect(text).toContain(word)
    for (const alt of ["Notizzettel", "Agent-Notizen", "Meine Ideen", "leeren", "Scratchpad"]) expect(text).not.toContain(alt)
  })

  it("beschreibt einzelne Ideen, nicht mehr den Zettel mit zwei Bereichen (en)", () => {
    const text = read("i18n", "help", "en", "scratchpad.md")
    expect(text.startsWith("# Ideas\n")).toBe(true)
    for (const word of ["headline", "description", "project", "status", "note"]) expect(text.toLowerCase()).toContain(word)
    for (const alt of ["notepad", "Agent Notes", "My Ideas", "Scratchpad"]) expect(text).not.toContain(alt)
  })

  it("nennt in beiden Sprachen dieselben Statusstufen wie das Modul", () => {
    const de = read("i18n", "help", "de", "scratchpad.md")
    const en = read("i18n", "help", "en", "scratchpad.md")
    for (const label of ["Neu", "Wird geprüft", "Geplant", "Geparkt", "Umgesetzt", "Verworfen"]) expect(de).toContain(`**${label}**`)
    for (const label of ["New", "Under review", "Planned", "Parked", "Done", "Dropped"]) expect(en).toContain(`**${label}**`)
  })

  it("heißt im Handbuch Ideen / Ideas", () => {
    expect(topics("de").scratchpad).toBe("Ideen")
    expect(topics("en").scratchpad).toBe("Ideas")
  })

  it("der Notizbuch-Artikel verweist auf Ideen statt auf den Zettel", () => {
    expect(read("i18n", "help", "de", "notizbuch.md")).not.toContain("Scratchpad")
    expect(read("i18n", "help", "en", "notizbuch.md")).not.toContain("Scratchpad")
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
