import { describe, expect, it } from "vitest"
import { shareAddresses } from "./shareAddress"

describe("Adresse der Projekt-Freigabe", () => {
  it("Linux: Windows-Schreibweise zuerst, dazu smb:// für den Finder", () => {
    expect(shareAddresses("linux", "hydra.local", "Mein_Projekt")).toEqual({
      primary: "\\\\hydra.local\\Mein_Projekt", secondary: "smb://hydra.local/Mein_Projekt",
    })
  })
  it("Mac: smb:// zuerst (Finder → Mit Server verbinden), dazu Windows-Schreibweise", () => {
    expect(shareAddresses("mac", "192.168.1.20", "P")).toEqual({
      primary: "smb://192.168.1.20/P", secondary: "\\\\192.168.1.20\\P",
    })
  })
  it("ohne Plattform-Angabe (ältere Server) wie Linux", () => {
    expect(shareAddresses(undefined, "h", "P").primary).toBe("\\\\h\\P")
  })
})
