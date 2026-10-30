import { describe, expect, it } from "vitest"
import { isManaged, visibleTabs } from "./managedAgent"
import de from "@/i18n/locales/de/agents.json"
import en from "@/i18n/locales/en/agents.json"

const TABS = ["overview", "model", "tools", "mail", "skills", "soul", "advanced", "schedules"].map((id) => ({ id }))

describe("verwaltete Agenten", () => {
  it("erkennt managed_by nur bei nicht-leerem Text", () => {
    expect(isManaged({ managed_by: "hydralabor" })).toBe(true)
    for (const v of [undefined, null, ""]) expect(isManaged({ managed_by: v as string | null | undefined })).toBe(false)
  })

  it("verwaltet: nur Übersicht, Modell, Intervalle", () => {
    expect(visibleTabs(TABS, { managed_by: "hydralabor" }).map((t) => t.id)).toEqual(["overview", "model", "schedules"])
  })

  it("normal: alle Reiter wie bisher", () => {
    expect(visibleTabs(TABS, {}).map((t) => t.id)).toEqual(TABS.map((t) => t.id))
  })

  it("Hinweis in beiden Sprachen, mit Modulname", () => {
    for (const l of [de, en] as const) {
      const m = (l as unknown as { managed?: { hint?: string } }).managed
      expect(m?.hint).toContain("{{module}}")
    }
  })
})
