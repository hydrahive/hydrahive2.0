import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}|${JSON.stringify(o)}` : k) }),
}))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn() } }))
import { AuditRow, type AuditEntry } from "./AreaAuditLog"

const base: AuditEntry = { at: "2026-11-28T01:02:03Z", actor: "anna", action: "tool_pool_set", target: "agent:abc",
  target_kind: "agent", target_name: "Mailhelfer", areas: ["Dateien lesen"], tools: ["file_read", "<img onerror=x>"], unknown: [] }

describe("AuditRow – ganze Sätze, Ziel aufgelöst, Tool-Namen nur Experte (Review #795)", () => {
  it("baut den Satz mit Akteur, Aktion und aufgelöstem Ziel – kein rohes agent:<id>", () => {
    const html = renderToStaticMarkup(<AuditRow e={base} expert={false} />)
    expect(html).toContain("areas.audit_sentence")
    expect(html).toContain("areas.target.agent")
    expect(html).toContain("Mailhelfer")
    expect(html).not.toContain("agent:abc")
    expect(html).not.toContain("file_read")
  })
  it("Tool-Namen nur in der Expertenansicht, und nur als Text", () => {
    const html = renderToStaticMarkup(<AuditRow e={base} expert />)
    expect(html).toContain("file_read")
    expect(html).not.toContain("<img")
  })
  it("Werkzeuge ohne Bereich werden gezählt statt verschwiegen", () => {
    const html = renderToStaticMarkup(<AuditRow e={{ ...base, areas: [], unknown: ["x", "y"] }} expert={false} />)
    expect(html).toContain("areas.audit_unknown")
    expect(html).toContain("&quot;count&quot;:2")
  })
})
