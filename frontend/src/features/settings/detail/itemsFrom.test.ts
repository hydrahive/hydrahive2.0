// Plan docs/plans/meine-einstellungen-kompakt.md, Task 2: Einträge für das Auswahlfeld.
import { describe, expect, it } from "vitest"
import type { Agent } from "@/features/agents/types"
import type { Project } from "@/features/projects/types"
import { agentItems, projectItems } from "./itemsFrom"

const agent = (id: string, name: string, type: Agent["type"], status: Agent["status"] = "active") =>
  ({ id, name, type, status, llm_model: `m-${id}` }) as Agent
const project = (id: string, name: string, status: Project["status"] = "active") => ({ id, name, status }) as Project

describe("agentItems", () => {
  const list = agentItems([
    agent("s", "Zeta", "specialist"), agent("p", "Beta", "project"), agent("m", "Omega", "master"), agent("p2", "Alpha", "project"),
  ])
  it("sortiert Master → Projekt-Agent → Spezialist, dann nach Name", () => {
    expect(list.map((i) => i.id)).toEqual(["m", "p2", "p", "s"])
  })
  it("Zusatz nennt Typ und Modell", () => {
    expect(list[0].detail).toBe("Master · m-m")
    expect(list[1].detail).toBe("Projekt-Agent · m-p2")
    expect(list[3].detail).toBe("Spezialist · m-s")
  })
  it("deaktivierte Agenten sind gedimmt und als „aus“ markiert", () => {
    const [off] = agentItems([agent("x", "Aus", "specialist", "disabled")])
    expect(off.dim).toBe(true)
    expect(off.detail).toBe("Spezialist · m-x · aus")
  })
})

describe("projectItems", () => {
  it("aktive zuerst, dann pausiert, dann archiviert, je nach Name (wie die bisherige Liste)", () => {
    const list = projectItems([project("c", "Alpha", "archived"), project("b", "Beta", "paused"), project("z", "Zeta"), project("a", "Gamma")])
    expect(list.map((i) => i.id)).toEqual(["a", "z", "b", "c"])
    expect(list.map((i) => Boolean(i.dim))).toEqual([false, false, true, true])
    expect(list[2].detail).toBe("pausiert")
    expect(list[3].detail).toBe("archiviert")
  })
})
