import { describe, expect, it } from "vitest"
import { updateOutcome } from "./_updateLogStatus"

const L = (...lines: string[]) => lines.map((l) => l + "\n")

describe("Update-Ergebnis aus dem Log (nur Zeilen NACH dem Start dieses Laufs)", () => {
  it("Mac: abgeschlossen", () => {
    expect(updateOutcome(L("[2026-10-22 18:45:47] Update gestartet", "[x] Service neu starten",
      "[2026-10-22 18:46:34] Update abgeschlossen", "HH-UPDATE-ENDE: ok"), 0)).toEqual({ kind: "ok" })
  })
  it("Mac: abgebrochen mit Grund", () => {
    expect(updateOutcome(L("[t] Update gestartet", "[t] npm ci fehlgeschlagen",
      "HH-UPDATE-ENDE: fehler npm ci fehlgeschlagen"), 0))
      .toEqual({ kind: "error", reason: "npm ci fehlgeschlagen" })
  })
  it("Linux-Farbcodes stören nicht", () => {
    expect(updateOutcome(L("\u001b[1;36m[hh2-update]\u001b[0m Update erfolgreich, Service läuft.",
      "HH-UPDATE-ENDE: ok"), 0)).toEqual({ kind: "ok" })
  })
  it("läuft noch: keine Schlusszeile", () => {
    expect(updateOutcome(L("[t] Update gestartet", "[t] Python-Pakete aktualisieren"), 0)).toEqual({ kind: "running" })
  })
  it("Schlusszeile eines FRÜHEREN Laufs zählt nicht", () => {
    const old = L("[t] Update gestartet", "HH-UPDATE-ENDE: ok")
    expect(updateOutcome([...old, ...L("[t2] Update gestartet", "[t2] Python-Pakete aktualisieren")], old.length))
      .toEqual({ kind: "running" })
    expect(updateOutcome([...old], old.length)).toEqual({ kind: "running" })
  })
  it("leerer Grund → fehler ohne Text", () => {
    expect(updateOutcome(L("HH-UPDATE-ENDE: fehler"), 0)).toEqual({ kind: "error", reason: "" })
  })
  it("nur exakte Schlusszeile am Zeilenanfang", () => {
    expect(updateOutcome(L("echo HH-UPDATE-ENDE: ok steht im Skript"), 0)).toEqual({ kind: "running" })
  })
})
