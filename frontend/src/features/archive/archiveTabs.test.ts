// Plan docs/plans/admin-reiter-archiv.md, Task 3: Reiter des Archiv-Fensters.
import { describe, expect, it } from "vitest"
import type { ArchiveStatus, OrphanScan } from "./api"
import { ARCHIVE_TABS, archiveTabs, parseArchiveTab } from "./archiveTabs"

const STATUS = { target: "local", storage: {}, share: {} } as unknown as ArchiveStatus
const job = { id: "j", name: "x" } as never
const KEINE_WAISEN: OrphanScan = { workspaces: [], agents: [], complete: true }
const t = (k: string) => k
const reiter = (s: ArchiveStatus | null, o: OrphanScan | null = KEINE_WAISEN, n = 0) =>
  Object.fromEntries(archiveTabs(s, o, n, t).map((r) => [r.id, r]))

describe("Archiv-Reiter", () => {
  it("drei Reiter in fester Reihenfolge, Rückfall auf Speicher", () => {
    expect(ARCHIVE_TABS).toEqual(["speicher", "vorgaenge", "inhalt"])
    expect(parseArchiveTab(null)).toBe("speicher")
    expect(parseArchiveTab("inhalt")).toBe("inhalt")
    expect(parseArchiveTab("quatsch")).toBe("speicher")
  })

  it("Inhalt zeigt die Anzahl der Einträge", () => {
    expect(reiter(STATUS, KEINE_WAISEN, 12).inhalt.count).toBe(12)
  })

  it("Vorgänge: kein Punkt, wenn nichts läuft und keine Waisen da sind", () => {
    expect(reiter(STATUS).vorgaenge.dot).toBe(false)
    expect(reiter(null, null).vorgaenge.dot).toBe(false)
  })

  it("Vorgänge: Punkt bei laufendem, wartendem Auftrag oder Umzug", () => {
    expect(reiter({ ...STATUS, jobs: { running: job, queued: [], done: [] } }).vorgaenge.dot).toBe(true)
    expect(reiter({ ...STATUS, jobs: { running: null, queued: [job], done: [] } }).vorgaenge.dot).toBe(true)
    expect(reiter({ ...STATUS, move: { running: {} as never, last: null } }).vorgaenge.dot).toBe(true)
  })

  it("Vorgänge: Punkt, wenn Waisen gefunden sind", () => {
    expect(reiter(STATUS, { workspaces: [{ id: "w" } as never], agents: [], complete: true }).vorgaenge.dot).toBe(true)
    expect(reiter(STATUS, { workspaces: [], agents: [{ id: "a" } as never], complete: true }).vorgaenge.dot).toBe(true)
  })

  it("Beschriftung aus der Übersetzung", () => {
    expect(reiter(STATUS).speicher.label).toBe("tabs.speicher")
  })
})
