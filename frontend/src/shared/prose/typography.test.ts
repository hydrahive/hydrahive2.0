import { describe, expect, it } from "vitest"
import { typographyFor } from "./typography"

describe("typographyFor", () => {
  it("Deutsch: „…“, ‚…‘ und Halbgeviertstrich, auch mit Region", () => {
    expect(typographyFor("de")).toMatchObject({ openDoubleQuote: "„", closeDoubleQuote: "“", emDash: "–" })
    expect(typographyFor("de-AT").openSingleQuote).toBe("‚")
  })
  it("Englisch und unbekannte Sprachen: “…” und Geviertstrich", () => {
    expect(typographyFor("en-GB")).toMatchObject({ openDoubleQuote: "“", emDash: "—" })
    expect(typographyFor("xx").closeDoubleQuote).toBe("”")
    expect(typographyFor(undefined).openDoubleQuote).toBe("“")
  })
})
