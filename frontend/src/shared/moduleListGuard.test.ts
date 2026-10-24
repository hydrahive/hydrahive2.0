import { readdirSync, readFileSync, statSync } from "node:fs"
import { join, relative } from "node:path"
import ts from "typescript"
import { describe, expect, it } from "vitest"

// Task 08c5c546: Modul-Listen aus @/modules/index.generated dürfen im Kern nicht
// beim Laden einer Datei gelesen werden (oberste Ebene), sonst sind sie bei
// einer Lade-Schleife (Modul importiert Kern-Datei) noch leer → Absturz.
// Ausnahmen: App.tsx und i18n/index.ts werden nur aus main.tsx geladen,
// nachdem index.generated fertig ist; kein Modul importiert sie.
const SRC = join(__dirname, "..")
const ALLOWED = new Set(["App.tsx", "i18n/index.ts"])

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) return name === "modules" && dir === SRC ? [] : files(p)
    return /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name) ? [p] : []
  })
}

/** Namen, die beim Laden (außerhalb von Funktionen) gelesen werden. */
export function eagerModuleReads(code: string, fileName = "x.tsx"): string[] {
  const sf = ts.createSourceFile(fileName, code, ts.ScriptTarget.Latest, true)
  const imported = new Set<string>()
  for (const st of sf.statements) {
    if (ts.isImportDeclaration(st) && (st.moduleSpecifier as ts.StringLiteral).text === "@/modules/index.generated") {
      const nb = st.importClause?.namedBindings
      if (nb && ts.isNamedImports(nb)) nb.elements.forEach((e) => { if (!e.isTypeOnly) imported.add(e.name.text) })
    }
  }
  const hits: string[] = []
  const visit = (n: ts.Node) => {
    if (ts.isFunctionLike(n) || ts.isImportDeclaration(n)) return
    if (ts.isIdentifier(n) && imported.has(n.text)) hits.push(n.text)
    ts.forEachChild(n, visit)
  }
  sf.statements.forEach(visit)
  return hits
}

describe("Wächter: Modul-Listen nicht beim Laden lesen", () => {
  it("erkennt Lesen auf oberster Ebene, ignoriert Funktionen", () => {
    const imp = `import { moduleX } from "@/modules/index.generated"\n`
    expect(eagerModuleReads(imp + "const a = moduleX as unknown[]")).toEqual(["moduleX"])
    expect(eagerModuleReads(imp + "export const L = [1, ...(moduleX as number[])]")).toEqual(["moduleX"])
    expect(eagerModuleReads(imp + "for (const b of moduleX) {}")).toEqual(["moduleX"])
    expect(eagerModuleReads(imp + "export function f() { return moduleX }")).toEqual([])
    expect(eagerModuleReads(imp + "const f = () => moduleX")).toEqual([])
    expect(eagerModuleReads(`const moduleX = 1\nconst a = moduleX`)).toEqual([])
  })

  it("keine Kern-Datei liest Modul-Listen beim Laden", () => {
    const bad = files(SRC)
      .map((p) => ({ rel: relative(SRC, p), hits: eagerModuleReads(readFileSync(p, "utf8"), p) }))
      .filter((f) => f.hits.length > 0 && !ALLOWED.has(f.rel))
      .map((f) => `${f.rel}: ${f.hits.join(", ")}`)
    expect(bad).toEqual([])
  })
})
