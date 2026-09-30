import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("./api", () => ({ apiKeysApi: { list: vi.fn(async () => []), create: vi.fn(), delete: vi.fn() } }))

import { ApiKeysSection } from "./ApiKeysSection"

describe("ApiKeysSection", () => {
  it("zeigt im Profil den eigenen Titel (Task 9e9439ff)", () => {
    const html = renderToStaticMarkup(<ApiKeysSection own />)
    expect(html).toContain("apikeys.own_title")
    expect(html).toContain("apikeys.own_subtitle")
    expect(html).not.toContain(">apikeys.title<")
  })

  it("zeigt im Admin-Cockpit den Admin-Titel", () => {
    const html = renderToStaticMarkup(<ApiKeysSection />)
    expect(html).toContain("apikeys.title")
    expect(html).not.toContain("apikeys.own_title")
  })
})
