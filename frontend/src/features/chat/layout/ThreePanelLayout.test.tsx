// docs/specs/chat-mobile-compact.md (Nachtrag): Die Werkstatt sitzt seit 0e6df831 in einem 10-px-Rahmen.
// Der alte Ausgleich -m-4/-m-6 ließ die Dreispalten-Ansicht 6–14 px über den Rahmen ragen.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
import { ThreePanelLayout } from "./ThreePanelLayout"

describe("ThreePanelLayout", () => {
  const outer = () => {
    const html = renderToStaticMarkup(<ThreePanelLayout left={<i>L</i>} center={<i>C</i>} right={<i>R</i>} />)
    return (html.match(/^<div class="([^"]*)"/)?.[1] ?? "").split(/\s+/)
  }

  it("füllt genau seinen Rahmen", () => {
    const cls = outer()
    expect(cls).toContain("h-full")
    expect(cls).toContain("overflow-hidden")
  })

  it("ragt nicht über den Rahmen (kein negativer Rand, keine Übergröße)", () => {
    const cls = outer()
    expect(cls.filter((c) => /^(md:)?-m-/.test(c))).toEqual([])
    expect(cls.filter((c) => c.includes("calc(100%+"))).toEqual([])
  })
})
