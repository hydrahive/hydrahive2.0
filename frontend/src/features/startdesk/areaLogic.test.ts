// docs/specs/startdesktop.md: Apps auf Bereiche verteilen, Bereich zu einem Pfad finden, Einstieg je Bereich.
import { describe, expect, it } from "vitest"
import type { LucideIcon } from "lucide-react"
import type { NavItem } from "@/shared/nav-config"
import { AREAS, HIDDEN_PATHS, OTHER_AREA } from "./areas"
import { areaForPath, entryPath, fillAreas, orderForMenu } from "./areaLogic"

const I = {} as LucideIcon
const item = (path: string, extra: Partial<NavItem> = {}): NavItem => ({ path, icon: I, labelKey: path.slice(1), group: "working", ...extra })
const ids = (xs: { area: { id: string } }[]) => xs.map((x) => x.area.id)

describe("Bereichs-Tabelle", () => {
  it("hat die acht freigegebenen Bereiche in fester Reihenfolge, Verwaltung nur für Admins", () => {
    expect(AREAS.map((a) => a.id)).toEqual(["medien", "schreiben", "wissen", "agenten", "kommunikation", "zuhause", "freizeit", "verwaltung"])
    expect(AREAS.filter((a) => a.adminOnly).map((a) => a.id)).toEqual(["verwaltung"])
  })
  it("Kennungen sind einfache Namen (passen zum Server-Format)", () => {
    for (const a of [...AREAS, OTHER_AREA]) expect(a.id).toMatch(/^[a-z0-9-]{1,32}$/)
  })
  it("kein Pfad steht in zwei Bereichen", () => {
    const all = AREAS.flatMap((a) => a.paths)
    expect(new Set(all).size).toBe(all.length)
  })
  it("Beispiel-Modul, Hilfe und Projekt-Einstellungen werden nicht gezeigt", () => {
    expect(HIDDEN_PATHS).toEqual(expect.arrayContaining(["/example", "/help", "/settings/projects"]))
  })
})

describe("fillAreas", () => {
  const visible = [item("/storyteller"), item("/notizbuch"), item("/studio"), item("/admin"), item("/example"), item("/neuesmodul"), item("/tonstudio")]

  it("verteilt nach Tabelle, Reihenfolge wie in der Tabelle", () => {
    const got = fillAreas(visible, true)
    const medien = got.find((g) => g.area.id === "medien")!
    expect(medien.items.map((i) => i.path)).toEqual(["/studio", "/tonstudio"])
  })
  it("leere Bereiche entfallen, Unbekanntes landet in Weitere am Ende, Verstecktes nirgends", () => {
    const got = fillAreas(visible, true)
    expect(ids(got)).toEqual(["medien", "schreiben", "verwaltung", "weitere"])
    expect(got.at(-1)!.items.map((i) => i.path)).toEqual(["/neuesmodul"])
    expect(got.flatMap((g) => g.items.map((i) => i.path))).not.toContain("/example")
  })
  it("Nicht-Admin: keine Verwaltung, deren sichtbare Apps in Weitere", () => {
    const got = fillAreas(visible, false)
    expect(ids(got)).not.toContain("verwaltung")
    expect(got.find((g) => g.area.id === "weitere")!.items.map((i) => i.path)).toEqual(["/admin", "/neuesmodul"])
  })
  it("Modul-Angabe area hat Vorrang vor der Tabelle", () => {
    const got = fillAreas([item("/studio", { area: "freizeit" }), item("/neuesmodul", { area: "wissen" })], true)
    expect(got.find((g) => g.area.id === "freizeit")!.items.map((i) => i.path)).toEqual(["/studio"])
    expect(got.find((g) => g.area.id === "wissen")!.items.map((i) => i.path)).toEqual(["/neuesmodul"])
    expect(ids(got)).not.toContain("medien")
  })
  it("unbekannte area-Angabe → Tabelle bzw. Weitere", () => {
    const got = fillAreas([item("/studio", { area: "gibtsnicht" })], true)
    expect(ids(got)).toEqual(["medien"])
  })
  it("Admin-Bereich per area-Angabe bleibt für Nicht-Admins zu", () => {
    const got = fillAreas([item("/neuesmodul", { area: "verwaltung" })], false)
    expect(ids(got)).toEqual(["weitere"])
  })
  it("doppelte Pfade zählen einmal", () => {
    const got = fillAreas([item("/studio"), item("/studio")], true)
    expect(got[0].items).toHaveLength(1)
  })
})

describe("areaForPath", () => {
  const areas = fillAreas([item("/settings"), item("/settings/agents"), item("/studio"), item("/storyteller")], true)
  it("findet den Bereich auch für Unterseiten", () => {
    expect(areaForPath(areas, "/studio/neu/123")!.area.area.id).toBe("medien")
    expect(areaForPath(areas, "/storyteller")!.item.path).toBe("/storyteller")
  })
  it("längster passender Pfad gewinnt", () => {
    const hit = areaForPath(areas, "/settings/agents/x")!
    expect(hit.item.path).toBe("/settings/agents")
    expect(hit.area.area.id).toBe("agenten")
    expect(areaForPath(areas, "/settings/llm")!.area.area.id).toBe("verwaltung")
  })
  it("kein Treffer bei ähnlichem Anfang ohne Schrägstrich, und bei fremden Seiten", () => {
    expect(areaForPath(areas, "/studioX")).toBeNull()
    expect(areaForPath(areas, "/profile")).toBeNull()
  })
})

describe("entryPath", () => {
  const areas = fillAreas([item("/storyteller"), item("/notizbuch")], true)
  const schreiben = areas.find((g) => g.area.id === "schreiben")!
  it("ohne Merker die erste App", () => {
    expect(entryPath(schreiben, {})).toBe("/storyteller")
  })
  it("mit Merker die zuletzt benutzte App, auch eine Unterseite", () => {
    expect(entryPath(schreiben, { schreiben: "/notizbuch" })).toBe("/notizbuch")
    expect(entryPath(schreiben, { schreiben: "/notizbuch/abc" })).toBe("/notizbuch/abc")
  })
  it("Merker auf eine App, die es nicht (mehr) gibt → erste App", () => {
    expect(entryPath(schreiben, { schreiben: "/studio" })).toBe("/storyteller")
    expect(entryPath(schreiben, { schreiben: "/notizbuchX" })).toBe("/storyteller")
  })
})

describe("orderForMenu", () => {
  const areas = fillAreas([item("/storyteller"), item("/studio"), item("/projects")], true)
  it("aktueller Bereich zuerst, Rest in fester Reihenfolge", () => {
    expect(ids(orderForMenu(areas, "agenten"))).toEqual(["agenten", "medien", "schreiben"])
    expect(ids(orderForMenu(areas, null))).toEqual(["medien", "schreiben", "agenten"])
  })
  it("Suche filtert Apps nach Anzeigename, leere Bereiche fallen weg", () => {
    const label = (i: NavItem) => ({ "/storyteller": "Storyteller", "/studio": "Studio (Film)", "/projects": "Projekte" })[i.path]!
    const got = orderForMenu(areas, null, "stu", label)
    expect(ids(got)).toEqual(["medien"])
    expect(got[0].items.map((i) => i.path)).toEqual(["/studio"])
    expect(ids(orderForMenu(areas, null, "  STORY ", label))).toEqual(["schreiben"])
  })
})
