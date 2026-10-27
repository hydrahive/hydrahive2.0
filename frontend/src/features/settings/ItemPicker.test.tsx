// Plan docs/plans/meine-einstellungen-kompakt.md, Task 3: Auswahlfeld (Darstellung; Bedienung prüft die GUI-Reise).
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { ItemPicker } from "./ItemPicker"

const items = [{ id: "1", name: "admin's Assistant", detail: "Master · claude-sonnet-4-6" }, { id: "2", name: "Prüfer", detail: "Spezialist" }]
const noop = () => {}

describe("ItemPicker", () => {
  it("zeigt Label und den gewählten Eintrag, zugeklappt", () => {
    const html = renderToStaticMarkup(<ItemPicker label="Agent" items={items} value="1" onChange={noop} />)
    expect(html).toContain(">Agent<")
    expect(html).toMatch(/role="combobox"[^>]*aria-expanded="false"|aria-expanded="false"[^>]*role="combobox"/)
    expect(html).toContain("admin&#x27;s Assistant")
    expect(html).not.toContain('role="listbox"')
  })
  it("„+ Neu“ nur, wenn Anlegen möglich ist", () => {
    expect(renderToStaticMarkup(<ItemPicker label="Agent" items={items} value="1" onChange={noop} />)).not.toContain("Neu")
    expect(renderToStaticMarkup(<ItemPicker label="Agent" items={items} value="1" onChange={noop} onCreate={noop} />)).toContain("Neu")
  })
  it("ohne Einträge: Hinweis statt leerem Feld", () => {
    expect(renderToStaticMarkup(<ItemPicker label="Projekt" items={[]} value={null} onChange={noop} />)).toContain("Keine Einträge")
  })
})
