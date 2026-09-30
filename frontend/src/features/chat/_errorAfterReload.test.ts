import { describe, expect, it } from "vitest"
import { errorAfterReload } from "./_reloadMerge"

const refusal = { loadedFor: "A", error: "Das Modell hat die Antwort abgelehnt …", errorKind: "refusal" }

describe("errorAfterReload", () => {
  it("behält einen Lauf-Fehler beim Live-Sync-Reload derselben Session (Task 891f1d3a)", () => {
    expect(errorAfterReload(refusal, "A")).toEqual({ error: refusal.error, errorKind: "refusal" })
  })

  it("behält Fehler ohne kind (z. B. leere Antwort, LLM-Call fehlgeschlagen)", () => {
    const s = { loadedFor: "A", error: "leere Antwort", errorKind: null }
    expect(errorAfterReload(s, "A")).toEqual({ error: "leere Antwort", errorKind: null })
  })

  it("behält max_iterations wie bisher (c8c591a7)", () => {
    const s = { loadedFor: "A", error: "Max", errorKind: "max_iterations" }
    expect(errorAfterReload(s, "A")).toEqual({ error: "Max", errorKind: "max_iterations" })
  })

  it("wirft den Fehler beim Session-Wechsel weg", () => {
    expect(errorAfterReload(refusal, "B")).toEqual({ error: null, errorKind: null })
  })

  it("wirft einen Lade-Fehler weg, sobald das Laden wieder klappt", () => {
    const s = { loadedFor: "A", error: "Netzwerk weg", errorKind: "load" }
    expect(errorAfterReload(s, "A")).toEqual({ error: null, errorKind: null })
  })

  it("bleibt leer, wenn kein Fehler da ist", () => {
    expect(errorAfterReload({ loadedFor: "A", error: null, errorKind: null }, "A"))
      .toEqual({ error: null, errorKind: null })
  })
})
