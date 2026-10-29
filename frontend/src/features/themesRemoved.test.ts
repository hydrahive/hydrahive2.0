// Task 3c82a8d5 (Plan docs/plans/themes-entfernen.md): Es gibt nur noch ein Design.
// Wächter gegen Reste des Layout-Theme-Systems. Das Farbschema (shared/theme.ts) und die
// Box-Themen (shared/brand/boxThemes.ts) sind etwas anderes und bleiben.
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs"
import { join, relative } from "node:path"
import { describe, expect, it } from "vitest"

const FE = join(__dirname, "..", "..")
const SRC = join(FE, "src")
const SELF = __filename

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n)
    if (statSync(p).isDirectory()) return n === "modules" ? [] : files(p)
    return /\.(tsx?|mjs|css)$/.test(n) && p !== SELF ? [p] : []
  })
}

describe("Layout-Themes sind entfernt", () => {
  it("die Theme-Ordner und der Generator sind weg", () => {
    for (const p of ["src/themes", "src/shared/themes", "src/shared/layouts", "src/features/themes",
      "src/features/themeeditor", "src/features/themetemplates", "src/features/profile/ThemePicker.tsx",
      "src/features/cockpit/admin/ThemesOverlay.tsx", "scripts/gen-themes.mjs", "public/kacheln/themes.webp"]) {
      expect(existsSync(join(FE, p)), p).toBe(false)
    }
  })
  it("App.tsx: keine Seitenvorlagen und keine Theme-Routen", () => {
    const app = readFileSync(join(SRC, "App.tsx"), "utf8")
    expect(app).not.toContain("ThemedPage")
    for (const r of ["themes", "theme-editor", "template-proof"]) expect(app).not.toContain(`path="${r}"`)
  })
  it("package.json: kein Theme-Generator, kein GrapesJS", () => {
    const pkg = readFileSync(join(FE, "package.json"), "utf8")
    expect(pkg).not.toContain("gen-themes")
    expect(pkg).not.toContain("grapesjs")
  })
  it("kein Quelltext verweist mehr auf das Theme-System", () => {
    const bad = /hh-active-theme"\)|hh-theme-change|shared\/themes|shared\/layouts|themetemplates|themeeditor|features\/themes\//
    const hits = [...files(SRC), ...files(join(FE, "scripts"))]
      .filter((f) => bad.test(readFileSync(f, "utf8"))).map((f) => relative(FE, f))
    expect(hits).toEqual([])
  })
})
