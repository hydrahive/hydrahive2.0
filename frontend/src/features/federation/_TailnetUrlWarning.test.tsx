import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
import { TailnetUrlWarning } from "./_TailnetUrlWarning"

describe("Warnung bei Adresse außerhalb des Tailnets", () => {
  it("LAN-Adresse: Warnung", () => {
    const html = renderToStaticMarkup(<TailnetUrlWarning url="https://192.168.178.186" />)
    expect(html).toContain("peers.url_not_tailnet")
  })
  it("Tailscale-Adresse: nichts", () => {
    expect(renderToStaticMarkup(<TailnetUrlWarning url="https://100.93.121.97" />)).toBe("")
  })
  it("leeres Feld: nichts (noch nicht ausgefüllt)", () => {
    expect(renderToStaticMarkup(<TailnetUrlWarning url="  " />)).toBe("")
  })
})
