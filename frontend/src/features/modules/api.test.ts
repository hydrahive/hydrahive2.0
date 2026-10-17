import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "t" }) } }))
vi.mock("@/i18n", () => ({ default: { t: (k: string, o?: Record<string, unknown>) => `${k}|${JSON.stringify(o?.module ?? "")}` } }))
vi.mock("@/features/vault/vaultStore", () => ({ useVaultStore: { getState: () => ({ token: null }) }, VAULT_401_CODES: [] }))
import { updateModule } from "./api"

afterEach(() => { vi.unstubAllGlobals() })

describe("Modul-Stream", () => {
  it("409: zeigt den übersetzten Fehlertext statt „HTTP 409“", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: { code: "module_operation_busy", params: { module: "studio" } } }), { status: 409 })))
    const msg = await new Promise<string>((resolve) => { updateModule("example", () => {}, () => resolve("done"), resolve) })
    expect(msg).toBe('errors:module_operation_busy|"studio"')
  })

  it("Fehler ohne lesbaren Inhalt: weiter „HTTP …“", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("kaputt", { status: 502 })))
    const msg = await new Promise<string>((resolve) => { updateModule("example", () => {}, () => resolve("done"), resolve) })
    expect(msg).toBe("HTTP 502")
  })

  it("Zeilen und Abschluss wie bisher", async () => {
    const body = 'data: {"line": "a"}\n\ndata: {"line": "b"}\n\ndata: {"done": true}\n\n'
    vi.stubGlobal("fetch", vi.fn(async () => new Response(body, { status: 200 })))
    const lines: string[] = []
    await new Promise<void>((resolve, reject) => { updateModule("example", (l) => lines.push(l), resolve, reject) })
    expect(lines).toEqual(["a", "b"])
  })
})
