import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
import { TailscaleBrowserLogin } from "./_TailscaleBrowserLogin"
import { isTailscaleLoginUrl } from "./_tailscaleLoginUrl"

const noop = () => {}

describe("Tailscale: Anmeldung im Browser", () => {
  it("ohne Link: Knopf", () => {
    const html = renderToStaticMarkup(<TailscaleBrowserLogin url={null} busy={false} error={null} onStart={noop} />)
    expect(html).toContain("tailscale.login_browser")
    expect(html).not.toContain("<a ")
  })
  it("mit Link: Link öffnet in neuem Tab, ohne Referrer", () => {
    const url = "https://login.tailscale.com/a/abc123"
    const html = renderToStaticMarkup(<TailscaleBrowserLogin url={url} busy={false} error={null} onStart={noop} />)
    expect(html).toContain(`href="${url}"`)
    expect(html).toContain('target="_blank"')
    expect(html).toContain("noopener")
    expect(html).not.toContain("tailscale.login_browser")
  })
  it("fremde Links werden nie als Link gezeigt", () => {
    const html = renderToStaticMarkup(<TailscaleBrowserLogin url="https://evil.example/a/x" busy={false} error={null} onStart={noop} />)
    expect(html).not.toContain("evil.example")
    expect(isTailscaleLoginUrl("javascript:alert(1)")).toBe(false)
    expect(isTailscaleLoginUrl("https://login.tailscale.com.evil/x")).toBe(false)
  })
  it("wartet: Knopf gesperrt", () => {
    const html = renderToStaticMarkup(<TailscaleBrowserLogin url={null} busy={true} error={null} onStart={noop} />)
    expect(html).toContain("tailscale.login_waiting")
    expect(html).toMatch(/<button[^>]*disabled/)
  })
})
