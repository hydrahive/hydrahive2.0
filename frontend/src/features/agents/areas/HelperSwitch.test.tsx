import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import { HelperView } from "./HelperView"
import type { Area } from "./types"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))

const area = (id: string, tools: string[], marks: Area["marks"] = []): Area =>
  ({ id, group: "files_code", name: `Name-${id}`, sentence: `Satz-${id}`, marks, tools, source: "core" })
const AREAS = [area("files_read", ["file_read"]), area("delegate", ["ask_agent"], ["costly"])]
const props = { areas: AREAS, forbidden: ["ask_agent"], onToggleEnabled: () => {}, onToggleArea: () => {}, onSave: () => {}, busy: false, dirty: false }

describe("HelperView – AB7", () => {
  it("aus: keine Bereichsliste, nur der Schalter", () => {
    const html = renderToStaticMarkup(<HelperView {...props} enabled={false} selected={[]} mayEdit />)
    expect(html).toContain("areas.helper_title"); expect(html).not.toContain("Name-files_read")
  })
  it("an: Bereichsliste, nicht Vergebbares ausgegraut mit Begründung", () => {
    const html = renderToStaticMarkup(<HelperView {...props} enabled selected={["files_read"]} mayEdit />)
    expect(html).toContain("Name-files_read"); expect(html).toContain("Name-delegate")
    expect(html).toContain("areas.helper_never")
    expect(html).toMatch(/data-area="delegate"[^>]*aria-disabled="true"/)
    expect(html).not.toMatch(/data-area="files_read"[^>]*aria-disabled="true"/)
  })
  it("zeigt keine Tool-Namen", () => {
    const html = renderToStaticMarkup(<HelperView {...props} enabled selected={["files_read"]} mayEdit />)
    expect(html).not.toContain("file_read"); expect(html).not.toContain("ask_agent")
  })
  it("ohne Recht: gesperrt, kein Speichern-Knopf", () => {
    const html = renderToStaticMarkup(<HelperView {...props} enabled selected={["files_read"]} mayEdit={false} />)
    expect(html).not.toContain("areas.helper_save")
    expect(html).toMatch(/role="switch"[^>]*\sdisabled=""/)
  })
})
