// Gefunden 20.10.2026: Eine Änderung auf der Admin-Seite, bevor die Einstellungen geladen waren, schickte einen leeren
// Platzhalter und löschte alle Anbieter. Jetzt: einzelne Zwecke gezielt speichern; vollständiges Speichern erst nach Laden.
import { beforeEach, describe, expect, it, vi } from "vitest"

const put = vi.fn(async (_url: string, _body: unknown) => ({}))
vi.mock("@/shared/api-client", () => ({ api: { put: (url: string, body: unknown) => put(url, body), get: vi.fn(), post: vi.fn(), delete: vi.fn() } }))

import { llmApi } from "../api"
import { configLoaded, purposeFor } from "../defaultModelSave"

beforeEach(() => put.mockClear())

describe("einzelnes Modell gezielt speichern", () => {
  it("schickt nur den Zweck und das Modell", async () => {
    await llmApi.setDefault("lessons", "off")
    expect(put).toHaveBeenCalledWith("/llm/default/lessons", { model: "off" })
  })
  it("Zwecke der Auswahl-Felder", () => {
    expect(purposeFor("chat")).toBe("chat")
    expect(purposeFor("stt")).toBe("stt")
    expect(purposeFor("lessons")).toBe("lessons")
    expect(purposeFor("embed")).toBeNull()                                        // braucht das volle Speichern
  })
})

describe("vollständiges Speichern erst nach dem Laden", () => {
  it("Platzhalter gilt nicht als geladen", () => {
    expect(configLoaded(null)).toBe(false)
    expect(configLoaded({ providers: [], default_model: "", embed_model: "" })).toBe(true)  // echt leer geladen ist ok
  })
})
