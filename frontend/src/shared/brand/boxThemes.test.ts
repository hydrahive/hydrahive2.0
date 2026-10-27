// Plan docs/plans/hydra-box-koepfe.md, Task 1: fester Hydra-Kopf je Box-Thema.
import { existsSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"
import { ADMIN_OVERLAY_THEME, BOX_THEMES } from "./boxThemes"
import { isAdminOverlayId } from "@/features/cockpit/admin/adminOverlayRegistry"

const PUBLIC = join(__dirname, "../../../public")
const OVERLAY_IDS = ["users", "modules", "plugins", "credentials", "themes", "mcp", "llm", "extensions", "system",
  "system-settings", "containers", "vms", "nodes", "jobs", "scheduled-tasks", "access", "archive", "federation", "zahnfee"]

describe("BOX_THEMES", () => {
  it("fünf Themen mit den fünf Köpfen", () => {
    expect(Object.fromEntries(Object.entries(BOX_THEMES).map(([k, v]) => [k, v.name]))).toEqual({
      wissen: "Professor", werkzeug: "Macher", status: "Denker", ideen: "Träumer", kontakt: "Buddy",
    })
  })
  it("jedes Kopfbild liegt wirklich in public/", () => {
    for (const t of Object.values(BOX_THEMES)) expect(existsSync(join(PUBLIC, t.head)), t.head).toBe(true)
  })
  it("passende Köpfe: Professor = Brille, Macher = orange, Denker = türkis, Träumer = lila, Buddy = mint", () => {
    expect(BOX_THEMES.wissen.head).toContain("kopf-5-brille")
    expect(BOX_THEMES.werkzeug.head).toContain("kopf-3-orange")
    expect(BOX_THEMES.status.head).toContain("kopf-4-tuerkis")
    expect(BOX_THEMES.ideen.head).toContain("kopf-2-lila")
    expect(BOX_THEMES.kontakt.head).toContain("kopf-1-mint")
  })
})

describe("ADMIN_OVERLAY_THEME", () => {
  it("jedes Admin-Fenster hat ein Thema", () => {
    for (const id of OVERLAY_IDS) {
      expect(isAdminOverlayId(id), id).toBe(true)
      expect(Object.keys(BOX_THEMES)).toContain(ADMIN_OVERLAY_THEME[id as keyof typeof ADMIN_OVERLAY_THEME])
    }
  })
  it("Beispiele der festen Zuordnung", () => {
    expect([ADMIN_OVERLAY_THEME.modules, ADMIN_OVERLAY_THEME.llm, ADMIN_OVERLAY_THEME.users, ADMIN_OVERLAY_THEME.system])
      .toEqual(["werkzeug", "ideen", "kontakt", "status"])
  })
})
