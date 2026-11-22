// Projekt-Zuordnung und „Nicht zugeordnet“ (federation-shared-tasks.md §Korrektur im Cockpit,
// §Projekte, die es nur auf einer Seite gibt; G3/P3).
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), put: vi.fn(), post: vi.fn() } }))
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o?.name ? `${k}:${o.name}` : k) }),
}))
import { ProjectMapTable } from "./_ProjectMapTable"
import { UnassignedSection } from "./_UnassignedSection"
import {
  canCreateHere, createPayload, groupUnassigned, hintFor, isUnassigned, type OriginProject,
} from "./_projectMap"

const origin = (over: Partial<OriginProject> = {}): OriginProject => ({
  origin_fp: "fp-home", origin_name: "hydrahome", origin_project_id: "op1", project_name: "  Garten  ",
  count: 3, setting: "auto", local_project_id: null, hidden: false, reason: "no_match", ...over,
})

describe("Logik", () => {
  it("Hinweis nur bei mehrdeutig / kein gleichnamiges / nicht Mitglied / Ziel nicht verfügbar", () => {
    for (const r of ["ambiguous", "no_match", "not_member", "target_unavailable"] as const) {
      expect(hintFor(origin({ reason: r }))).toBe(r)
    }
    for (const r of ["manual", "name", "hidden", "no_project"] as const) {
      expect(hintFor(origin({ reason: r }))).toBeNull()
    }
  })
  it("nicht zugeordnet = kein lokales Projekt und nicht „nicht anzeigen“", () => {
    expect(isUnassigned(origin())).toBe(true)
    expect(isUnassigned(origin({ local_project_id: "p1", reason: "name" }))).toBe(false)
    expect(isUnassigned(origin({ hidden: true, reason: "hidden" }))).toBe(false)
  })
  it("„Projekt hier anlegen“ nur bei kein gleichnamiges Projekt und mit Namen", () => {
    expect(canCreateHere(origin())).toBe(true)
    expect(canCreateHere(origin({ reason: "ambiguous" }))).toBe(false)
    expect(canCreateHere(origin({ reason: "not_member" }))).toBe(false)
    expect(canCreateHere(origin({ project_name: "   " }))).toBe(false)
  })
  it("Nutzlast für POST /api/projects: Name getrimmt, nur der Nutzer als Mitglied, Standardwerte", () => {
    expect(createPayload(origin(), "till")).toEqual(
      { name: "Garten", description: "", members: ["till"], template: "", init_git: false },
    )
  })
  it("gruppiert nach Instanz, zugeordnete fallen heraus", () => {
    const g = groupUnassigned([
      origin(), origin({ origin_project_id: "op2", local_project_id: "p1", reason: "name" }),
      origin({ origin_fp: "fp-vps", origin_name: "hydrahive-vps", origin_project_id: "op3", reason: "ambiguous" }),
    ])
    expect(g.map(x => [x.instance, x.rows.map(r => r.origin_project_id)])).toEqual(
      [["hydrahome", ["op1"]], ["hydrahive-vps", ["op3"]]],
    )
  })
})

const table = (origins: OriginProject[]) => renderToStaticMarkup(
  <ProjectMapTable origins={origins} projects={[{ id: "p1", name: "Hydrahive DEV" }]} busy={null} errors={{}}
                   onChange={() => {}} />,
)

describe("Tabelle „Projekt-Zuordnung“", () => {
  it("Spalten, Auswahl automatisch / Projekt … / nicht anzeigen, Hinweis", () => {
    const h = table([origin({ reason: "ambiguous" })])
    for (const k of ["map.col_instance", "map.col_origin_project", "map.col_count", "map.col_target", "map.col_hint"]) {
      expect(h).toContain(k)
    }
    expect(h).toContain("hydrahome")
    expect(h).toContain('value="auto"')
    expect(h).toContain('value="p1"')
    expect(h).toContain("map.target_project:Hydrahive DEV")
    expect(h).toContain('value="hidden"')
    expect(h).toContain("reason.ambiguous")
  })
  it("verschwundenes Ziel bleibt wählbar markiert", () => {
    const h = table([origin({ setting: "weg", reason: "target_unavailable" })])
    expect(h).toContain("map.target_unavailable_option")
    expect(h).toContain("reason.target_unavailable")
  })
  it("leer: Hinweis statt Tabelle", () => {
    expect(table([])).toContain("map.empty")
    expect(table([])).not.toContain("<table")
  })
})

const unassigned = (isAdmin: boolean, origins: OriginProject[], errors: Record<string, string> = {}) =>
  renderToStaticMarkup(
    <UnassignedSection origins={origins} isAdmin={isAdmin} busy={null} errors={errors} onCreate={() => {}} />,
  )

describe("Bereich „Nicht zugeordnet“", () => {
  it("Admin sieht den Knopf bei „kein gleichnamiges Projekt“", () => {
    const h = unassigned(true, [origin()])
    expect(h).toContain("<button")
    expect(h).toContain("unassigned.create:Garten")
    expect(h).not.toContain("unassigned.admin_can_create")
  })
  it("Nicht-Admin sieht nur den Hinweis", () => {
    const h = unassigned(false, [origin()])
    expect(h).not.toContain("<button")
    expect(h).toContain("unassigned.admin_can_create")
  })
  it("kein Knopf bei mehrdeutig oder nicht Mitglied, auch für Admins", () => {
    const h = unassigned(true, [origin({ reason: "ambiguous" }), origin({ origin_project_id: "op2", reason: "not_member" })])
    expect(h).not.toContain("<button")
    expect(h).not.toContain("unassigned.admin_can_create")
    expect(h).toContain("reason.ambiguous")
    expect(h).toContain("reason.not_member")
  })
  it("Fehler der Route wird angezeigt", () => {
    const h = unassigned(true, [origin()], { "fp-home\u0000op1": "Name ungültig" })
    expect(h).toContain("Name ungültig")
  })
  it("alles zugeordnet: Leerhinweis", () => {
    expect(unassigned(true, [origin({ local_project_id: "p1", reason: "name" })])).toContain("unassigned.empty")
  })
})
