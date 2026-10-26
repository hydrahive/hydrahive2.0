// Plan docs/plans/admin-luecken-schliessen.md, Task 4: Reiter des Föderations-Fensters.
import { describe, expect, it } from "vitest"
import { FEDERATION_TABS, parseFederationTab } from "./federationTabs"

describe("Föderations-Reiter", () => {
  it("vier Reiter in fester Reihenfolge", () => {
    expect(FEDERATION_TABS).toEqual(["workstations", "peers", "clients", "datamining"])
  })
  it("ohne Angabe: Workstations", () => {
    expect(parseFederationTab(null)).toBe("workstations")
  })
  it("gültiger Reiter bleibt", () => {
    expect(parseFederationTab("peers")).toBe("peers")
    expect(parseFederationTab("datamining")).toBe("datamining")
  })
  it("unbekannter Reiter fällt auf Workstations zurück", () => {
    expect(parseFederationTab("quatsch")).toBe("workstations")
  })
})
