import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

// i18n zieht @/modules/index.generated – das entsteht erst beim Build (in CI fehlt es). Für den api-client reicht t().
vi.mock("@/i18n", () => ({ default: { t: (k: string, o?: { defaultValue?: string }) => o?.defaultValue ?? k } }))
import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { useVaultStore } from "./vaultStore"

function respond(status: number, body: unknown, headers: Record<string, string> = {}) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...headers } }))
}

describe("api-client und Vault", () => {
  const fetchMock = vi.fn()
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock)
    useAuthStore.setState({ token: "jwt", username: "u", role: "user" })
    useVaultStore.setState({ token: null, prompt: null })
  })
  afterEach(() => { vi.unstubAllGlobals(); fetchMock.mockReset() })

  it("schickt den Vault-Token mit, wenn vorhanden", async () => {
    useVaultStore.setState({ token: "vt1" })
    fetchMock.mockReturnValueOnce(respond(200, { ok: true }))
    await api.get("/modules/patientenakte/x")
    expect(fetchMock.mock.calls[0][1].headers["X-HH-Vault"]).toBe("vt1")
  })

  it("übernimmt den verlängerten Token aus X-HH-Vault-Refresh", async () => {
    useVaultStore.setState({ token: "vt1" })
    fetchMock.mockReturnValueOnce(respond(200, { ok: true }, { "X-HH-Vault-Refresh": "vt2" }))
    await api.get("/modules/patientenakte/x")
    expect(useVaultStore.getState().token).toBe("vt2")
  })

  it("423 vault_locked öffnet den PIN-Dialog und vergisst den alten Token", async () => {
    useVaultStore.setState({ token: "alt" })
    fetchMock.mockReturnValueOnce(respond(423, { detail: { code: "vault_locked", params: { pin_set: false } } }))
    await expect(api.get("/credentials")).rejects.toThrow()
    expect(useVaultStore.getState().prompt).toEqual({ pinSet: false })
    expect(useVaultStore.getState().token).toBeNull()
  })

  it("falsche PIN (401 vault_pin_wrong) loggt NICHT aus", async () => {
    fetchMock.mockReturnValueOnce(respond(401, { detail: { code: "vault_pin_wrong" } }))
    await expect(api.post("/vault/unlock", { pin: "000000" })).rejects.toThrow()
    expect(useAuthStore.getState().token).toBe("jwt")
  })

  it("echtes 401 (abgelaufener Login) loggt weiter aus", async () => {
    fetchMock.mockReturnValueOnce(respond(401, { detail: { code: "token_expired" } }))
    await expect(api.get("/sessions")).rejects.toThrow()
    expect(useAuthStore.getState().token).toBeNull()
  })
})
