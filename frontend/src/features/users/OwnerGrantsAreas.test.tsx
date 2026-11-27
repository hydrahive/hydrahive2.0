// Agenten-Bereiche, Aufgabe 7 (AB8): Besitzer-Freigabe speichert über /api/admin/tool-grants/{user} (Tool-Namen, kein kategorie:x).
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k, i18n: { language: "de" } }) }))
const seen: { path?: string } = {}
vi.mock("@/features/agents/areas/PoolAreasEditor", () => ({
  PoolAreasEditor: (p: { path: string }) => { seen.path = p.path; return <div data-part="editor" /> },
}))
import { OwnerGrantsAreas } from "./OwnerGrantsAreas"

describe("OwnerGrantsAreas", () => {
  it("nutzt die bestehende Route der Besitzer-Freigabe, Nutzername kodiert", () => {
    renderToStaticMarkup(<OwnerGrantsAreas username="anna maria" />)
    expect(seen.path).toBe("/admin/tool-grants/anna%20maria")
  })
})
