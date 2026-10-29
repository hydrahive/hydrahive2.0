// Task 308b7c91 (Till 29.10.: „mache a“): Das Medien-Cockpit zeigt nur Projekte, in denen man Mitglied ist.
// Spiegel der Regel im Kern (projects/_members_model.role_of): created_by zählt, Mitglieder als
// Objekt oder (alt) als reiner Name.
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"
import { isProjectMember, ownProjects } from "./membership"

const p = (id: string, created_by: string, members: unknown[]) => ({ id, created_by, members }) as never

describe("isProjectMember", () => {
  it("Ersteller ist Mitglied", () => expect(isProjectMember(p("a", "till", []), "till")).toBe(true))
  it("Mitglied mit Rolle", () => expect(isProjectMember(p("a", "x", [{ username: "till", role: "read" }]), "till")).toBe(true))
  it("altes Format: nur der Name", () => expect(isProjectMember(p("a", "x", ["till"]), "till")).toBe(true))
  it("fremdes Projekt", () => expect(isProjectMember(p("a", "x", [{ username: "bibi", role: "write" }]), "till")).toBe(false))
  it("ohne Benutzername nie", () => expect(isProjectMember(p("a", "", []), "")).toBe(false))
  it("fehlende Mitgliederliste bricht nicht", () => expect(isProjectMember({ id: "a", created_by: "x" } as never, "till")).toBe(false))
})

describe("ownProjects", () => {
  it("filtert auf eigene Projekte und behält die Reihenfolge", () => {
    const list = [p("fremd", "x", []), p("eigen1", "till", []), p("eigen2", "x", ["till"])]
    expect(ownProjects(list, "till").map((x: { id: string }) => x.id)).toEqual(["eigen1", "eigen2"])
  })
})

describe("Medien-Cockpit", () => {
  const src = readFileSync(join(__dirname, "..", "cockpit", "MediaCockpitPage.tsx"), "utf8")
  it("nutzt ownProjects für die Auswahl", () => {
    expect(src).toMatch(/ownProjects\(/)
  })
  it("unterscheidet „lädt noch“ von „kein eigenes Projekt“", () => {
    expect(src).toContain("Projekte laden…")
    expect(src).toContain("Kein eigenes Projekt")
  })
})
