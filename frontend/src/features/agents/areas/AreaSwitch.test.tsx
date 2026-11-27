import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import { AreaSwitch } from "./AreaSwitch"
import type { Area, AreaState } from "./types"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: { count?: number }) => (o?.count !== undefined ? `${k}:${o.count}` : k) }) }))

const area = (marks: Area["marks"] = []): Area => ({
  id: "files_write", group: "files_code", name: "Dateien ändern", sentence: "Dateien im Projekt anlegen, ändern und überschreiben",
  marks, tools: ["file_patch", "file_write"], source: "core",
})
const st = (over: Partial<AreaState> = {}): AreaState => ({ id: "files_write", state: "off", have: [], missing: [], new: [], via_category: [], ...over })
const render = (a: Area, s: AreaState, extra: object = {}) =>
  renderToStaticMarkup(<AreaSwitch area={a} state={s} disabled={false} onToggle={() => {}} onAdoptNew={() => {}} {...extra} />)

describe("AreaSwitch", () => {
  it("zeigt Name und Satz, aber keine Tool-Namen", () => {
    const html = render(area(), st())
    expect(html).toContain("Dateien ändern")
    expect(html).toContain("Dateien im Projekt anlegen")
    expect(html).not.toContain("file_write")
  })
  it("zeigt „teilweise“ als eigenen Zustand", () => {
    expect(render(area(), st({ state: "partial", have: ["file_read"] }))).toContain('data-state="partial"')
    expect(render(area(), st({ state: "on" }))).toContain('data-state="on"')
    expect(render(area(), st({ state: "off" }))).toContain('data-state="off"')
    expect(render(area(), st({ state: "partial" }))).toContain('aria-checked="mixed"')
  })
  it("zeigt die Zeichen ⚠️ 🔒 💶 mit title-Erklärung", () => {
    const html = render(area(["risky", "private", "costly"]), st())
    expect(html).toContain("⚠️"); expect(html).toContain("🔒"); expect(html).toContain("💶")
    expect(html).toContain('title="areas.mark_risky"'); expect(html).toContain('title="areas.mark_private"')
    expect(html).toContain('title="areas.mark_costly"')
  })
  it("ohne Markierung kein Zeichen", () => {
    const html = render(area([]), st())
    expect(html).not.toContain("⚠️"); expect(html).not.toContain("🔒"); expect(html).not.toContain("💶")
  })
  it("zeigt den Übernehmen-Hinweis nur bei new", () => {
    expect(render(area(), st({ state: "on" }))).not.toContain("adopt-new")
    const html = render(area(), st({ state: "on", missing: ["a", "b"], new: ["a", "b"] }))
    expect(html).toContain("adopt-new"); expect(html).toContain("areas.new_tools:2")
  })
  it("zeigt bei Kategorie-Anteil ehrlich woher der Rest kommt", () => {
    expect(render(area(), st({ state: "partial", via_category: ["file_read"] }))).toContain("areas.via_category")
    expect(render(area(), st({ state: "off" }))).not.toContain("areas.via_category")
  })
  it("gesperrt: Schalter disabled", () => {
    expect(render(area(), st(), { disabled: true })).toMatch(/<button[^>]*role="switch"[^>]*disabled/)
    expect(render(area(), st(), { disabled: false })).not.toMatch(/role="switch"[^>]*disabled/)
  })
})
