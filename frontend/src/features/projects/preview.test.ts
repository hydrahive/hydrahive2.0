import { describe, expect, it, vi } from "vitest"
import { openPreviewTab, previewLoginUrl, PREVIEW_PROXY_PORT } from "./preview"

function fakeTab() {
  return { opener: {} as unknown, location: { replace: vi.fn() }, close: vi.fn() }
}

describe("Testseite öffnen (Durchreiche :8445)", () => {
  it("Adresse: Name aus der aktuellen Adresse, Port 8445, Ticket im Login-Pfad", () => {
    expect(PREVIEW_PROXY_PORT).toBe(8445)
    expect(previewLoginUrl("localhost", "abc")).toBe("https://localhost:8445/__hh_preview_login?t=abc")
    expect(previewLoginUrl("hydra.tail1234.ts.net", "a-b_c")).toBe("https://hydra.tail1234.ts.net:8445/__hh_preview_login?t=a-b_c")
  })

  it("Ticket wird kodiert, nichts Fremdes in der Adresse", () => {
    expect(previewLoginUrl("h", "x&y=1")).toBe("https://h:8445/__hh_preview_login?t=x%26y%3D1")
  })

  it("öffnet den Tab SOFORT (im Klick) und setzt danach die Adresse mit dem Ticket aus der API", async () => {
    const tab = fakeTab()
    const calls: string[] = []
    const open = vi.fn((url: string) => { calls.push(`open:${url}`); return tab })
    const getTicket = vi.fn(async () => { calls.push("ticket"); return { ticket: "T1" } })
    expect(await openPreviewTab(open, getTicket, "192.168.1.5")).toBe(true)
    expect(calls).toEqual(["open:about:blank", "ticket"])          // erst Tab, dann Ticket → kein Popup-Blocker
    expect(open).toHaveBeenCalledWith("about:blank", "_blank")
    expect(tab.opener).toBeNull()                                     // wie noopener: Testseite kommt nicht an HydraHive
    expect(tab.location.replace).toHaveBeenCalledWith("https://192.168.1.5:8445/__hh_preview_login?t=T1")
  })

  it("Ticket schlägt fehl: leeren Tab schließen, Fehler weitergeben", async () => {
    const tab = fakeTab()
    await expect(openPreviewTab(() => tab, async () => { throw new Error("Kein Zugriff") }, "h")).rejects.toThrow("Kein Zugriff")
    expect(tab.close).toHaveBeenCalled()
    expect(tab.location.replace).not.toHaveBeenCalled()
  })

  it("Popup blockiert: kein Ticket holen, false melden", async () => {
    const getTicket = vi.fn(async () => ({ ticket: "T" }))
    expect(await openPreviewTab(() => null, getTicket, "h")).toBe(false)
    expect(getTicket).not.toHaveBeenCalled()
  })
})
