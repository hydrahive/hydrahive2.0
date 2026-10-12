import { renderToStaticMarkup } from "react-dom/server"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}[${Object.entries(o).map(([a, b]) => `${a}=${b}`).join(",")}]` : k) }),
}))
const apiMock = vi.hoisted(() => ({ lock: vi.fn(), adminReset: vi.fn(), status: vi.fn() }))
vi.mock("./api", () => ({ vaultApi: apiMock }))

import { useVaultStore } from "./vaultStore"
import { VaultBadgeView } from "./VaultBadge"
import { lockNow, minutesLeft, resetVaultPin } from "./vaultActions"

describe("Vault-Abzeichen", () => {
  it("zeigt nichts, solange keine PIN existiert", () => {
    expect(renderToStaticMarkup(<VaultBadgeView status={{ pin_set: false, unlocked: false, remaining_seconds: 0, idle_seconds: 900 }} onLock={() => {}} />)).toBe("")
  })
  it("gesperrt: Schloss ohne Sperren-Knopf", () => {
    const html = renderToStaticMarkup(<VaultBadgeView status={{ pin_set: true, unlocked: false, remaining_seconds: 0, idle_seconds: 900 }} onLock={() => {}} />)
    expect(html).toContain("locked")
    expect(html).not.toContain("lock_now")
  })
  it("entsperrt: Restzeit in Minuten (aufgerundet) und Sperren-Knopf", () => {
    const html = renderToStaticMarkup(<VaultBadgeView status={{ pin_set: true, unlocked: true, remaining_seconds: 61, idle_seconds: 900 }} onLock={() => {}} />)
    expect(html).toContain("unlocked_for[min=2]")
    expect(html).toContain("lock_now")
  })
  it("minutesLeft rundet auf (1 s Rest → 1 min)", () => {
    expect(minutesLeft(1)).toBe(1)
    expect(minutesLeft(60)).toBe(1)
    expect(minutesLeft(61)).toBe(2)
    expect(minutesLeft(900)).toBe(15)
  })
})

describe("Jetzt sperren / Admin-Reset", () => {
  beforeEach(() => { apiMock.lock.mockReset(); apiMock.adminReset.mockReset() })
  afterEach(() => useVaultStore.setState({ token: null, prompt: null }))

  it("lockNow sperrt am Server und vergisst den Token", async () => {
    useVaultStore.setState({ token: "vt" })
    apiMock.lock.mockResolvedValueOnce({ ok: true })
    await lockNow()
    expect(apiMock.lock).toHaveBeenCalledOnce()
    expect(useVaultStore.getState().token).toBeNull()
  })
  it("lockNow vergisst den Token auch, wenn der Server nicht antwortet", async () => {
    useVaultStore.setState({ token: "vt" })
    apiMock.lock.mockRejectedValueOnce(new Error("offline"))
    await lockNow()
    expect(useVaultStore.getState().token).toBeNull()
  })
  it("resetVaultPin ruft den Admin-Reset mit der user_id", async () => {
    apiMock.adminReset.mockResolvedValueOnce({ ok: true })
    await resetVaultPin("u-42")
    expect(apiMock.adminReset).toHaveBeenCalledWith("u-42")
  })
})
