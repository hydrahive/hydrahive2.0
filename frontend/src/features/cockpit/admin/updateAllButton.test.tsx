// docs/specs/modul-update-alle.md: „Alle updaten“ nutzt EINEN Ablauf (useUpdateAll → updateAllModules), nicht mehr
// die Schleife über updateModule – die Schleife wurde vom Neustart nach dem ersten Modul abgerissen (Task b74c972d).
import { describe, expect, it } from "vitest"
import { readFileSync } from "node:fs"
import { join } from "node:path"

const src = (p: string) => readFileSync(join(__dirname, p), "utf8")

describe.each([
  ["Admin-Cockpit", "./ModulesOverlay.tsx"],
  ["Modul-Seite", "../../modules/ModulesPage.tsx"],
])("„Alle updaten“ (%s)", (_name, file) => {
  it("nutzt den gemeinsamen Ablauf useUpdateAll mit der Zahl offener Updates", () => {
    expect(src(file)).toMatch(/useUpdateAll\(outdated\.length,\s*load\)/)
  })
  it("fährt keine Schleife mehr über updateModule", () => {
    expect(src(file)).not.toMatch(/updateModule\(/)
  })
  it("zeigt Knopf und Ergebnis", () => {
    expect(src(file)).toMatch(/<UpdateAllButton\b/)
    expect(src(file)).toMatch(/<UpdateAllResult\b/)
  })
})

describe("useUpdateAll", () => {
  it("startet genau einen Aufruf updateAllModules und wertet die Zeilen mit parseUpdateAll aus", () => {
    const hook = src("../../modules/useUpdateAll.ts")
    expect(hook.match(/updateAllModules\(/g)).toHaveLength(1)
    expect(hook).toMatch(/parseUpdateAll\(/)
    expect(hook).not.toMatch(/updateModule\(/)
  })
})
