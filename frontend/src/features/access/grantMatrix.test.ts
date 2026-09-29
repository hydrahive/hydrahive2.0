import { describe, expect, it } from "vitest"
import { cellLevel, groupCapabilities, nextLevel, subjectsFor } from "./grantMatrix"
import type { AccessCatalog } from "./types"

const catalog: AccessCatalog = {
  capabilities: [
    { id: "core.vms", label: "VMs", default: "admin_only", module_id: "", tools: [],
      grants: [{ subject_type: "group", subject_id: "g1", level: "use" }] },
    { id: "module.ha", label: "HA", default: "everyone", module_id: "homeassistant", tools: [],
      grants: [{ subject_type: "everyone", subject_id: "", level: "use" }] },
    { id: "homeassistant.control", label: "Schalten", default: "admin_only", module_id: "homeassistant",
      tools: ["ha_call_service"], grants: [{ subject_type: "user", subject_id: "u1", level: "manage" }] },
  ],
  groups: [{ id: "g1", name: "Familie" }],
  users: [{ user_id: "u1", username: "anna", role: "user" }],
}

describe("grantMatrix", () => {
  it("liefert Spalten: Alle, Gruppen, Nutzer", () => {
    expect(subjectsFor(catalog).map((s) => s.key)).toEqual(["everyone:", "group:g1", "user:u1"])
  })

  it("liest die Stufe einer Zelle", () => {
    const [vms, ha, control] = catalog.capabilities
    expect(cellLevel(vms, "group", "g1")).toBe("use")
    expect(cellLevel(vms, "user", "u1")).toBeNull()
    expect(cellLevel(ha, "everyone", "")).toBe("use")
    expect(cellLevel(control, "user", "u1")).toBe("manage")
  })

  it("schaltet zyklisch: keine → benutzen → verwalten → keine", () => {
    expect(nextLevel(null)).toBe("use")
    expect(nextLevel("use")).toBe("manage")
    expect(nextLevel("manage")).toBeNull()
  })

  it("gruppiert: Core zuerst, dann je Modul", () => {
    const groups = groupCapabilities(catalog.capabilities)
    expect(groups.map((g) => g.module_id)).toEqual(["", "homeassistant"])
    expect(groups[1].items.map((c) => c.id)).toEqual(["module.ha", "homeassistant.control"])
  })
})
