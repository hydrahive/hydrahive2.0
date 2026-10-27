// Task 0dda5420: leere Seiten und 404 zeigen die bunte Hydra (Stimmungsbilder), nicht mehr die alte blaue.
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"

const SRC = join(__dirname, "..")
function files(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n)
    if (statSync(p).isDirectory()) return n === "modules" ? [] : files(p)
    return /\.(tsx?|css)$/.test(n) && !/\.test\./.test(n) ? [p] : []
  })
}

describe("alte Hydra-Bilder im Kern", () => {
  it("kein Kern-Code verweist mehr auf alte Leer-/404-/Zustandsbilder", () => {
    const old = /\/illustrations\/(empty-[a-z]+|404-confused|hydra-(idle|working|speaking|sleeping|confused|celebrate|thinking|error))\.png/
    const hits = files(SRC).filter((f) => old.test(readFileSync(f, "utf8"))).map((f) => f.replace(SRC, "src"))
    expect(hits).toEqual([])
  })
})
