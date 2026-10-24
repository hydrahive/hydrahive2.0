import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "t" }) } }))
vi.mock("@/i18n", () => ({ default: { t: (k: string, o?: Record<string, unknown>) => `${k}|${JSON.stringify(o?.module ?? "")}` } }))
vi.mock("@/features/vault/vaultStore", () => ({ useVaultStore: { getState: () => ({ token: null }) }, VAULT_401_CODES: [] }))
import { updateAllModules, updateModule } from "./api"

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

// docs/specs/modul-update-alle.md: ein Aufruf für alle Module statt einer Schleife im Browser.
describe("updateAllModules", () => {
  it("POST /api/admin/modules/update-all mit Anmeldung, Zeilen und Abschluss", async () => {
    const body = 'data: {"line": "x"}\n\ndata: {"done": true}\n\n'
    const fetchMock = vi.fn(async () => new Response(body, { status: 200 }))
    vi.stubGlobal("fetch", fetchMock)
    const lines: string[] = []
    await new Promise<void>((resolve, reject) => { updateAllModules((l) => lines.push(l), resolve, reject) })
    expect(lines).toEqual(["x"])
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe("/api/admin/modules/update-all")
    expect(init.method).toBe("POST")
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer t")
  })

  it("Fehler im Ablauf kommt als Fehler an", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response('data: {"error": "module_update_all_failed: a (x)"}\n\n', { status: 200 })))
    const msg = await new Promise<string>((resolve) => { updateAllModules(() => {}, () => resolve("done"), resolve) })
    expect(msg).toBe("module_update_all_failed: a (x)")
  })
})
