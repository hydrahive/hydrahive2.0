// Plan docs/plans/meine-einstellungen-kompakt.md, Task 4: innere Reiter nur bei mehreren Teilen, volle Fläche für Editoren.
import { renderToStaticMarkup } from "react-dom/server"
import type { ComponentType, LazyExoticComponent } from "react"
import { describe, expect, it } from "vitest"
import { Bot } from "lucide-react"
import { ContentArea } from "./ContentArea"
import type { SettingsGroup } from "./registry"

const C = (name: string) => (() => <div data-content={name} />) as unknown as LazyExoticComponent<ComponentType>
const group = (p: Partial<SettingsGroup>): SettingsGroup => ({ id: "g", label: "G", icon: Bot, tabs: [], ...p })

describe("ContentArea", () => {
  it("eine Gruppe mit einem Inhalt: keine innere Reiterleiste", () => {
    const html = renderToStaticMarkup(<ContentArea group={group({ component: C("one") })} />)
    expect(html).not.toContain('role="tab"')
    expect(html).toContain('data-content="one"')
  })
  it("genau ein benannter Teil (früher „Credentials“, „Flows“): ebenfalls keine Reiterleiste", () => {
    const html = renderToStaticMarkup(<ContentArea group={group({ tabs: ["Flows"], tabComponents: { Flows: C("f") } })} />)
    expect(html).not.toContain('role="tab"')
    expect(html).toContain('data-content="f"')
  })
  it("mehrere Teile: innere Reiter, erster ist gewählt und sichtbar", () => {
    const html = renderToStaticMarkup(<ContentArea group={group({ tabs: ["A", "B"], tabComponents: { A: C("a"), B: C("b") } })} />)
    expect(html.match(/role="tab"/g)).toHaveLength(2)
    expect(html).toMatch(/aria-selected="true"[^>]*>A</)
    expect(html).toContain('data-content="a"')
    expect(html).not.toContain('data-content="b"')
  })
  // Till 26.10.: Inhalt bei breiten Fenstern zentrieren (feste Höchstbreite), Editoren (wide) über die volle Breite.
  it("Inhalt sitzt mittig in fester Höchstbreite", () => {
    expect(renderToStaticMarkup(<ContentArea group={group({ component: C("x") })} />)).toMatch(/class="[^"]*mx-auto[^"]*max-w-5xl[^"]*"/)
    expect(renderToStaticMarkup(<ContentArea group={group({ component: C("x"), fullHeight: true })} />)).toMatch(/class="[^"]*mx-auto[^"]*max-w-5xl[^"]*"/)
  })
  it("wide (Butler-Editor): volle Breite, nicht zentriert", () => {
    expect(renderToStaticMarkup(<ContentArea group={group({ component: C("x"), fullHeight: true, wide: true })} />)).not.toContain("max-w-5xl")
  })
  it("fullHeight: kein Innenabstand, kein eigenes Scrollen", () => {
    expect(renderToStaticMarkup(<ContentArea group={group({ component: C("x"), fullHeight: true })} />)).toContain("overflow-hidden")
    expect(renderToStaticMarkup(<ContentArea group={group({ component: C("x") })} />)).toContain("overflow-y-auto p-4")
  })
})
