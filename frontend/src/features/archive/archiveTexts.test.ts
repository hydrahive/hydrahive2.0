import { describe, expect, it } from "vitest"
import de from "@/i18n/locales/de/archive.json"
import en from "@/i18n/locales/en/archive.json"

// Till, 13.10.: Viele Nutzer kennen wir nicht und haben keinen Zugriff auf deren Server. Kein Text darf
// auf Terminal, Config-Dateien oder Update-Skripte verweisen – alles geht über die Admin-Konsole.
const FORBIDDEN = /update\.sh|install\.conf|HH_[A-Z_]+|sudo|terminal|shell|\/etc\//i

function strings(obj: unknown, path = ""): [string, string][] {
  if (typeof obj === "string") return [[path, obj]]
  if (obj && typeof obj === "object") return Object.entries(obj).flatMap(([k, v]) => strings(v, path ? `${path}.${k}` : k))
  return []
}

describe("Archiv-Texte ohne Terminal-Anweisungen", () => {
  for (const [lang, texts] of [["de", de], ["en", en]] as const) {
    it(lang, () => {
      const bad = strings(texts).filter(([, s]) => FORBIDDEN.test(s))
      expect(bad).toEqual([])
    })
  }

  it("de und en haben dieselben Schlüssel", () => {
    expect(strings(en).map(([k]) => k).sort()).toEqual(strings(de).map(([k]) => k).sort())
  })
})
