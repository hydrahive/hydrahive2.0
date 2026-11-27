import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import { ToolsSelector } from "./ToolsSelector"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))

const tools = [{ name: "file_read", description: "", category: "files" }, { name: "web_search", description: "", category: "web" }]

describe("ToolsSelector – kategorie:x (Katalog 6b)", () => {
  it("zeigt kategorie:x-Einträge als entfernbare Chips", () => {
    const html = renderToStaticMarkup(
      <ToolsSelector available={tools} selected={["file_read", "kategorie:files"]} onChange={() => {}} />,
    )
    expect(html).toContain("category-entries")
    expect(html).toContain("kategorie:files")
  })
  it("ohne Kategorie-Einträge kein Chip-Bereich", () => {
    const html = renderToStaticMarkup(<ToolsSelector available={tools} selected={["file_read"]} onChange={() => {}} />)
    expect(html).not.toContain("category-entries")
  })
})
