// Task 0dda5420: Jede Emoticon-Datei im Ordner ist auch ein wählbares Kürzel – keine verwaisten Altbilder.
import { readdirSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"
import { EMOTE_NAMES } from "./_emoteNames.generated"

const DIR = join(__dirname, "..", "..", "..", "public", "illustrations", "emoticons")

describe("Emoticon-Dateien", () => {
  it("jede PNG im Ordner gehört zu einem Kürzel (keine Altlasten)", () => {
    const files = readdirSync(DIR).filter((f) => f.endsWith(".png")).sort()
    expect(files).toEqual(EMOTE_NAMES.map((n) => `hydra-${n}.png`).sort())
  })
})
