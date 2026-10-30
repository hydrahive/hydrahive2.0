// Plan docs/plans/admin-reiter-module.md, Task 1: Reiter, Suche und Reihenfolge im Module-Fenster.
import { describe, expect, it } from "vitest"
import type { ModuleEntry } from "@/features/modules/types"
import { MODULE_TABS, moduleTabs, moduleView, parseModuleTab } from "./moduleTabs"

const m = (id: string, p: Partial<ModuleEntry> = {}): ModuleEntry => ({
  id, name: id, description: "", installed: true, loaded: true, error: null,
  version: "1.0.0", available_version: "1.0.0", update_available: false, ...p,
})
const LISTE: ModuleEntry[] = [
  m("zebra"),
  m("mailbox", { name: "Mailbox", description: "Postfächer lesen" }),
  m("alpha", { update_available: true }),
  m("kaputt", { loaded: false, error: "ImportError" }),
  m("notizbuch", { installed: false, version: null, description: "Notizen und Mails ablegen" }),
  m("boardgames", { installed: false, version: null }),
]
const ids = (l: ModuleEntry[]) => l.map((x) => x.id)
const t = (k: string) => k

describe("Module-Reiter", () => {
  it("zwei Reiter, Rückfall auf Installiert", () => {
    expect(MODULE_TABS).toEqual(["installiert", "verfuegbar"])
    expect(parseModuleTab(null)).toBe("installiert")
    expect(parseModuleTab("verfuegbar")).toBe("verfuegbar")
    expect(parseModuleTab("x")).toBe("installiert")
  })

  it("Reihenfolge: Fehler, dann Update, dann nach Name", () => {
    expect(ids(moduleView(LISTE, "installiert", ""))).toEqual(["kaputt", "alpha", "mailbox", "zebra"])
  })

  it("Verfügbar zeigt nur nicht installierte Module, nach Name", () => {
    expect(ids(moduleView(LISTE, "verfuegbar", ""))).toEqual(["boardgames", "notizbuch"])
  })

  it("Suche über Name, Kennung und Beschreibung, ohne Rücksicht auf Groß/Klein, Rand-Leerzeichen egal", () => {
    expect(ids(moduleView(LISTE, "installiert", "MAILBOX"))).toEqual(["mailbox"])
    expect(ids(moduleView(LISTE, "installiert", "  postfächer "))).toEqual(["mailbox"])
    expect(ids(moduleView(LISTE, "verfuegbar", "mails"))).toEqual(["notizbuch"])
    expect(ids(moduleView(LISTE, "installiert", "gibtsnicht"))).toEqual([])
  })

  it("angeheftetes Modul bleibt im Reiter, obwohl es gerade installiert wurde", () => {
    const danach = LISTE.map((x) => (x.id === "boardgames" ? { ...x, installed: true, version: "1.0.0" } : x))
    expect(ids(moduleView(danach, "verfuegbar", "", new Map([["boardgames", "verfuegbar" as const]])))).toEqual(["boardgames", "notizbuch"])
    expect(ids(moduleView(danach, "installiert", "", new Map([["boardgames", "verfuegbar" as const]])))).not.toContain("boardgames")
  })

  it("Zähler = Treffer je Reiter, Punkt nur bei Installiert mit Update oder Fehler", () => {
    const r = Object.fromEntries(moduleTabs(LISTE, "", t).map((x) => [x.id, x]))
    expect(r.installiert.count).toBe(4)
    expect(r.verfuegbar.count).toBe(2)
    expect(r.installiert.dot).toBe(true)
    expect(r.verfuegbar.dot).toBeFalsy()
    const ruhig = Object.fromEntries(moduleTabs([m("a"), m("b", { installed: false })], "", t).map((x) => [x.id, x]))
    expect(ruhig.installiert.dot).toBe(false)
    expect(Object.fromEntries(moduleTabs(LISTE, "mail", t).map((x) => [x.id, x.count]))).toEqual({ installiert: 1, verfuegbar: 1 })
  })
})
