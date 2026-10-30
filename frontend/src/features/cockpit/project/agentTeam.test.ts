// Plan docs/plans/projekt-cockpit-kompakt.md: Projekt-Team kompakt (höchstens 5, gewählter immer sichtbar).
import { describe, expect, it } from "vitest"
import type { AgentBrief } from "@/features/chat/types"
import { teamList, visibleTeam } from "./agentTeam"

const a = (id: string, llm_model = "modell-a") => ({ id, name: `Agent ${id}`, llm_model }) as AgentBrief
const ALLE = Array.from({ length: 15 }, (_, i) => a(`s${i + 1}`, i === 11 ? "besonderes-modell" : "modell-a"))
const team = teamList([a("lead"), ...ALLE], "lead", ALLE.map((x) => x.id).concat(["s3", "unbekannt"]))
const ids = (l: AgentBrief[]) => l.map((x) => x.id)

describe("teamList", () => {
  it("Lead zuerst, doppelte und unbekannte IDs raus", () => {
    expect(team[0].id).toBe("lead")
    expect(team).toHaveLength(16)
    expect(ids(team)).not.toContain("unbekannt")
  })
})

describe("visibleTeam", () => {
  it("eingeklappt: höchstens 5, Rest als verborgen gezählt", () => {
    const v = visibleTeam(team, { selectedId: "lead", expanded: false, query: "", limit: 5 })
    expect(ids(v.shown)).toEqual(["lead", "s1", "s2", "s3", "s4"])
    expect(v.hidden).toBe(11)
  })
  it("der gewählte Agent ist immer sichtbar, auch wenn er weit hinten steht", () => {
    const v = visibleTeam(team, { selectedId: "s12", expanded: false, query: "", limit: 5 })
    expect(v.shown).toHaveLength(5)
    expect(ids(v.shown)).toContain("s12")
    expect(ids(v.shown)[0]).toBe("lead")
  })
  it("aufgeklappt: alle, nichts verborgen", () => {
    const v = visibleTeam(team, { selectedId: "lead", expanded: true, query: "", limit: 5 })
    expect(v.shown).toHaveLength(16)
    expect(v.hidden).toBe(0)
  })
  it("Suche über Name und Modell, ohne Rücksicht auf Groß/Klein – zeigt alle Treffer", () => {
    expect(ids(visibleTeam(team, { selectedId: "lead", expanded: false, query: "AGENT S1", limit: 5 }).shown))
      .toEqual(["s1", "s10", "s11", "s12", "s13", "s14", "s15"])
    expect(ids(visibleTeam(team, { selectedId: "lead", expanded: false, query: "besonderes", limit: 5 }).shown)).toEqual(["s12"])
  })
  it("kleines Team: alles sichtbar, nichts verborgen", () => {
    const klein = teamList([a("lead"), a("x")], "lead", ["x"])
    expect(visibleTeam(klein, { selectedId: "x", expanded: false, query: "", limit: 5 })).toEqual({ shown: klein, hidden: 0 })
  })
})
