// docs/specs/startdesktop.md (Punkt 5): Merker am Server. Fund im echten Test (24.10.): Wird eine Seite direkt
// aufgerufen, merkte sich die Leiste die App, BEVOR die Einstellungen geladen waren – und überschrieb am Server
// die Merker der anderen Bereiche. Änderungen vor dem Laden müssen mit dem Server-Stand zusammengeführt werden.
import { beforeEach, describe, expect, it, vi } from "vitest"

const api = vi.hoisted(() => ({ get: vi.fn(), patch: vi.fn() }))
vi.mock("@/features/preferences/api", () => ({ preferencesApi: api }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: () => "T" }))
import { useAreaPrefsStore } from "./useAreaPrefs"

const store = () => useAreaPrefsStore.getState()
const server = { active_area: "medien", area_last: { medien: "/tonstudio", schreiben: "/notizbuch" } }
const lastPatch = () => api.patch.mock.calls.at(-1)?.[0]

describe("useAreaPrefsStore", () => {
  beforeEach(() => {
    api.get.mockReset(); api.patch.mockReset(); api.patch.mockResolvedValue({})
    useAreaPrefsStore.setState({ active: null, last: {}, loadedFor: null, loaded: false, dirty: false })
  })

  it("nach dem Laden: Merker vom Server", async () => {
    api.get.mockResolvedValue(server)
    await store().load("T")
    expect(store().active).toBe("medien")
    expect(store().last).toEqual(server.area_last)
    expect(api.patch).not.toHaveBeenCalled()
  })

  it("Merken VOR dem Laden überschreibt den Server nicht, sondern wird zusammengeführt", async () => {
    let resolve!: (v: unknown) => void
    api.get.mockReturnValue(new Promise((r) => { resolve = r }))
    const loading = store().load("T")
    store().remember("verwaltung", "/settings")
    expect(api.patch).not.toHaveBeenCalled()
    resolve(server)
    await loading
    expect(store().last).toEqual({ medien: "/tonstudio", schreiben: "/notizbuch", verwaltung: "/settings" })
    expect(store().active).toBe("verwaltung")
    expect(lastPatch()).toEqual({ active_area: "verwaltung", area_last: { medien: "/tonstudio", schreiben: "/notizbuch", verwaltung: "/settings" } })
  })

  it("lokale Änderung vor dem Laden gewinnt für denselben Bereich", async () => {
    let resolve!: (v: unknown) => void
    api.get.mockReturnValue(new Promise((r) => { resolve = r }))
    const loading = store().load("T")
    store().remember("medien", "/studio")
    resolve(server)
    await loading
    expect(store().last.medien).toBe("/studio")
    expect(store().last.schreiben).toBe("/notizbuch")
  })

  it("Bereich wählen vor dem Laden wird nach dem Laden gespeichert, Merker bleiben", async () => {
    let resolve!: (v: unknown) => void
    api.get.mockReturnValue(new Promise((r) => { resolve = r }))
    const loading = store().load("T")
    store().setActive("wissen")
    resolve(server)
    await loading
    expect(store().active).toBe("wissen")
    expect(lastPatch()).toEqual({ active_area: "wissen", area_last: server.area_last })
  })

  it("nach dem Laden: Merken speichert sofort den vollständigen Stand", async () => {
    api.get.mockResolvedValue(server)
    await store().load("T")
    store().remember("schreiben", "/storyteller")
    expect(lastPatch()).toEqual({ active_area: "schreiben", area_last: { medien: "/tonstudio", schreiben: "/storyteller" } })
  })

  it("gleicher Merker → kein unnötiges Speichern", async () => {
    api.get.mockResolvedValue(server)
    await store().load("T")
    store().remember("medien", "/tonstudio")
    expect(api.patch).not.toHaveBeenCalled()
  })

  it("Laden scheitert → lokale Änderungen bleiben, Speichern danach möglich", async () => {
    api.get.mockRejectedValue(new Error("offline"))
    await store().load("T")
    store().remember("schreiben", "/storyteller")
    expect(store().last).toEqual({ schreiben: "/storyteller" })
    expect(lastPatch()).toEqual({ active_area: "schreiben", area_last: { schreiben: "/storyteller" } })
  })
})
