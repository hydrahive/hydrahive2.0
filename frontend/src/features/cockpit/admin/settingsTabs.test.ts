// Plan docs/plans/admin-reiter-einstellungen.md, Task 1: ein Reiter je Einstellungs-Gruppe.
import { describe, expect, it } from "vitest"
import type { EditableSetting } from "@/features/system/settingsApi"
import { groupSlug, parseGroup, settingGroups } from "./settingsTabs"

const s = (key: string, group: string) => ({ key, group }) as EditableSetting

describe("groupSlug", () => {
  it("klein, Leerzeichen zu Bindestrich", () => {
    expect(groupSlug("Home Assistant")).toBe("home-assistant")
    expect(groupSlug("AgentLink")).toBe("agentlink")
  })
  it("Umlaute umgeschrieben, Sonderzeichen zu einem Bindestrich, kein Rand-Bindestrich", () => {
    expect(groupSlug("Größe & Ä")).toBe("groesse-ae")
    expect(groupSlug("  Mail!  ")).toBe("mail")
  })
})

describe("settingGroups", () => {
  const LISTE = [s("a", "Websuche"), s("b", "Mail"), s("c", "Websuche"), s("d", "Home Assistant")]
  it("Gruppen in der Reihenfolge des Servers, mit ihren Einstellungen", () => {
    const g = settingGroups(LISTE)
    expect(g.map((x) => x.name)).toEqual(["Websuche", "Mail", "Home Assistant"])
    expect(g.map((x) => x.slug)).toEqual(["websuche", "mail", "home-assistant"])
    expect(g[0].settings.map((x) => x.key)).toEqual(["a", "c"])
  })
  it("leer bleibt leer", () => {
    expect(settingGroups([])).toEqual([])
  })
})

describe("parseGroup", () => {
  it("gültige Gruppe bleibt, sonst die erste, ohne Gruppen null", () => {
    expect(parseGroup(["websuche", "mail"], "mail")).toBe("mail")
    expect(parseGroup(["websuche", "mail"], "ueberblick")).toBe("websuche")
    expect(parseGroup(["websuche", "mail"], null)).toBe("websuche")
    expect(parseGroup([], "mail")).toBeNull()
  })
})
