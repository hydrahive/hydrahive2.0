// Task 3c82a8d5: Update brach auf bestehenden Installationen ab, weil die alte, nie
// eingecheckte src/themes/index.generated.ts liegen blieb. Das Aufräumskript läuft vor
// jedem Build und entfernt sie.
import { execFileSync } from "node:child_process"
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"
import { describe, expect, it } from "vitest"

const FE = join(__dirname, "..", "..")

function sandbox(): string {
  const dir = mkdtempSync(join(tmpdir(), "hh-legacy-"))
  mkdirSync(join(dir, "scripts"))
  cpSync(join(FE, "scripts", "cleanup-legacy.mjs"), join(dir, "scripts", "cleanup-legacy.mjs"))
  return dir
}

describe("cleanup-legacy.mjs", () => {
  it("entfernt den alten src/themes-Ordner samt generierter Datei", () => {
    const dir = sandbox()
    mkdirSync(join(dir, "src", "themes", "irgendein-theme"), { recursive: true })
    writeFileSync(join(dir, "src", "themes", "index.generated.ts"), 'import type { X } from "@/shared/themes/types"\n')
    execFileSync("node", [join(dir, "scripts", "cleanup-legacy.mjs")])
    expect(existsSync(join(dir, "src", "themes"))).toBe(false)
  })
  it("ohne Altlast: läuft still durch", () => {
    const dir = sandbox()
    expect(execFileSync("node", [join(dir, "scripts", "cleanup-legacy.mjs")]).toString()).toBe("")
  })
  it("läuft vor dem Build (prebuild) und vor dev", () => {
    const scripts = JSON.parse(readFileSync(join(FE, "package.json"), "utf8")).scripts
    expect(scripts.prebuild).toMatch(/^node scripts\/cleanup-legacy\.mjs && /)
    expect(scripts.dev).toMatch(/^node scripts\/cleanup-legacy\.mjs && /)
  })
})
