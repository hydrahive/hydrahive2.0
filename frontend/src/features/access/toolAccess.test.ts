import { describe, expect, it } from "vitest"
import { blockedTools } from "./toolAccess"
import type { MyAccess } from "./types"

const tools = [
  { name: "file_read", capability: null },
  { name: "ha_call_service", capability: "homeassistant.control" },
  { name: "ha_list_entities", capability: "module.homeassistant" },
  { name: "neu_tool", capability: "neu.x" },
]

const user: MyAccess = {
  admin: false,
  capabilities: { "module.homeassistant": "use" },
  declared: ["module.homeassistant", "homeassistant.control"],
  groups: [],
}

describe("blockedTools", () => {
  it("sperrt Werkzeuge mit deklarierter, fehlender Funktion", () => {
    expect([...blockedTools(tools, user)]).toEqual(["ha_call_service"])
  })

  it("Admin hat keine gesperrten Werkzeuge", () => {
    expect(blockedTools(tools, { ...user, admin: true }).size).toBe(0)
  })

  it("nicht deklarierte Funktion ist offen", () => {
    expect(blockedTools(tools, user).has("neu_tool")).toBe(false)
  })

  it("ohne Freigabe-Daten wird nichts gesperrt", () => {
    expect(blockedTools(tools, null).size).toBe(0)
  })
})
