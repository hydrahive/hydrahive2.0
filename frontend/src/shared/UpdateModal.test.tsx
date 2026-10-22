import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: { commit?: string }) => (o?.commit ? `${k}:${o.commit}` : k) }) }))
vi.mock("@/shared/dialog/useDialog", () => ({ useDialog: () => ({ props: {}, titelId: "t" }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: () => new Promise(() => {}) } }))
import { UpdateModal } from "./UpdateModal"

const noop = () => {}

describe("Update-Fenster: Abschluss", () => {
  it("neuer Stand → Version + Neu laden", () => {
    const html = renderToStaticMarkup(<UpdateModal state="done" newCommit="abc123" onConfirm={noop} onClose={noop} />)
    expect(html).toContain("update.done:abc123")
    expect(html).toContain("update.reload")
    expect(html).toContain("update.close")
  })
  it("nichts Neues → eigener Text, Knöpfe da", () => {
    const html = renderToStaticMarkup(<UpdateModal state="done" newCommit={null} onConfirm={noop} onClose={noop} />)
    expect(html).toContain("update.done_same")
    expect(html).not.toContain("update.done:")
    expect(html).toContain("update.close")
  })
  it("Fehler → Grund + Schließen", () => {
    const html = renderToStaticMarkup(<UpdateModal state="failed" errorMessage="npm ci fehlgeschlagen" onConfirm={noop} onClose={noop} />)
    expect(html).toContain("update.failed")
    expect(html).toContain("update.close")
  })
})
