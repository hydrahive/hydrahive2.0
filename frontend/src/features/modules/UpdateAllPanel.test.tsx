// docs/specs/modul-update-alle.md: Knopf-Text je Phase und Ergebnis (geklappt / nicht geklappt mit Grund).
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
import { UpdateAllButton, UpdateAllResult } from "./UpdateAllPanel"
import { parseUpdateAll } from "./updateAllProgress"
import type { UpdateAllState } from "./useUpdateAll"

const st = (lines: string[], running: boolean, error: string | null = null, total = 3): UpdateAllState =>
  ({ running, progress: parseUpdateAll(lines, total), error })
const unq = (h: string) => h.replace(/&quot;/g, '"')
const btn = (s: UpdateAllState, n = 3) => unq(renderToStaticMarkup(<UpdateAllButton outdatedCount={n} state={s} onStart={() => {}} buttonClass="b" />))
const res = (s: UpdateAllState) => unq(renderToStaticMarkup(<UpdateAllResult state={s} onDismiss={() => {}} />))

describe("UpdateAllButton", () => {
  it("ohne offene Updates und ohne Ablauf: kein Knopf", () => {
    expect(btn({ running: false, progress: null, error: null }, 0)).toBe("")
  })
  it("ruhend: „Alle updaten“, klickbar", () => {
    const h = btn({ running: false, progress: null, error: null })
    expect(h).toContain("update.all<")
    expect(h).not.toContain("disabled")
    expect(h).toContain('type="button"')
  })
  it("Module laufen: Zähler, gesperrt", () => {
    const h = btn(st(["[modules] update a …", "[modules] a: fertig (1 → 2)"], true))
    expect(h).toContain('update.all_running:{"done":1,"total":3}')
    expect(h).toContain("disabled")
  })
  it("Bauen und Neustart als eigene Texte", () => {
    expect(btn(st(["[modules] Frontend wird gebaut …"], true))).toContain("update.all_build")
    expect(btn(st(["[modules] Neustart angefordert"], true))).toContain("update.all_restart")
  })
})

describe("UpdateAllResult", () => {
  it("während des Ablaufs und vorher nichts", () => {
    expect(res(st([], true))).toBe("")
    expect(res({ running: false, progress: null, error: null })).toBe("")
  })
  it("alles geklappt: grün mit Anzahl", () => {
    const h = res(st(["[modules] a: fertig (1 → 2)", "[modules] b: fertig (1 → 2)", "[modules] Fertig: 2 aktualisiert, 0 fehlgeschlagen"], false))
    expect(h).toContain('update.all_done:{"count":2}')
    expect(h).toContain("emerald")
    expect(h).not.toContain("update.all_failed_title")
  })
  it("teils gescheitert: rot, Liste mit Grund", () => {
    const h = res(st(["[modules] a: fertig (1 → 2)", "[modules] archiver: FEHLER – Permission denied", "[modules] Fertig: 1 aktualisiert, 1 fehlgeschlagen"], false))
    expect(h).toContain('update.all_done_failed:{"ok":1,"failed":1}')
    expect(h).toContain("rose")
    expect(h).toMatch(/archiver<\/span> – Permission denied/)
  })
  it("alle gescheitert: Fehlermeldung des Servers, Liste mit Grund", () => {
    const h = res(st(["[modules] a: FEHLER – x"], false, "Kein Modul konnte aktualisiert werden: a (x)"))
    expect(h).toContain("Kein Modul konnte aktualisiert werden")
    expect(h).toMatch(/a<\/span> – x/)
  })
  it("bei Fehlern: Hinweis, was man tun kann (einzeln erneut, Protokoll)", () => {
    const h = res(st(["[modules] x: FEHLER – keine Schreibrechte auf den Modul-Ordner"], false))
    expect(h).toContain("update.all_failed_hint")
    expect(res(st(["[modules] a: fertig (1 → 2)"], false))).not.toContain("update.all_failed_hint")
  })
  it("nichts zu tun: „Alle Module sind aktuell“", () => {
    expect(res(st(["[modules] Alle Module sind aktuell"], false, null, 0))).toContain("update.all_uptodate")
  })
  it("ist eine Statusmeldung mit Schließen-Knopf", () => {
    const h = res(st(["[modules] a: fertig (1 → 2)"], false))
    expect(h).toContain('role="status"')
    expect(h).toMatch(/<button[^>]*type="button"[^>]*aria-label="update.all_close"/)
  })
})
