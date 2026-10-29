// Task 0dda5420: Auch die älteren Seiten-Layouts (Standard-Theme „Menü oben“, Seitenleiste) zeigen das neue Logo.
import { readFileSync, existsSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"

const DIR = __dirname
const PUBLIC = join(__dirname, "../../../public")

describe("Layouts nutzen das neue Logo", () => {
  for (const f of ["TopnavLayout.tsx", "SidebarLayout.tsx"]) {
    it(`${f}: HydraLogo statt alter logo-mark.png`, () => {
      const src = readFileSync(join(DIR, f), "utf8")
      expect(src).not.toContain("logo-mark")
      expect(src).toContain("<HydraLogo")
    })
  }
  it("alte logo-mark.png ist entfernt", () => {
    expect(existsSync(join(PUBLIC, "illustrations/logo-mark.png"))).toBe(false)
  })
})
