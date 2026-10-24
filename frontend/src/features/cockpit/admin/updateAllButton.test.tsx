// docs/specs/modul-update-alle.md: „Alle updaten“ nutzt EINEN Aufruf (updateAllModules), nicht mehr die Schleife
// über updateModule – die Schleife wurde vom Neustart nach dem ersten Modul abgerissen (Task b74c972d).
import { describe, expect, it } from "vitest"
import { readFileSync } from "node:fs"
import { join } from "node:path"

const src = (p: string) => readFileSync(join(__dirname, p), "utf8")

describe.each([
  ["Admin-Cockpit", "./ModulesOverlay.tsx"],
  ["Modul-Seite", "../../modules/ModulesPage.tsx"],
])("„Alle updaten“ (%s)", (_name, file) => {
  it("ruft updateAllModules auf", () => {
    expect(src(file)).toMatch(/updateAllModules\(/)
  })
  it("fährt keine Schleife mehr über updateModule", () => {
    expect(src(file)).not.toMatch(/updateModule\(/)
  })
  it("zeigt Fortschritt und Zusammenfassung über parseUpdateAll", () => {
    expect(src(file)).toMatch(/parseUpdateAll\(/)
  })
})
