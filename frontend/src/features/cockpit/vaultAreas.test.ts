import { describe, expect, it } from "vitest"
import { visibleVaultAreas, VAULT_AREAS } from "./vaultAreas"
import type { MyAccess } from "@/features/access/types"

const admin = { admin: true, declared: [], capabilities: {}, groups: [] } as unknown as MyAccess
const user = (caps: Record<string, boolean>, declared: string[]) =>
  ({ admin: false, declared, capabilities: caps, groups: [] }) as unknown as MyAccess

describe("visibleVaultAreas", () => {
  it("zeigt Modul-Bereiche nur, wenn das Modul installiert ist", () => {
    const owners = { "/akte": "patientenakte" }                       // nur die Akte installiert
    const ids = visibleVaultAreas(owners, admin).map((a) => a.id)
    expect(ids).toContain("akte")
    expect(ids).not.toContain("cryptoboard")
    expect(ids).not.toContain("haushaltsbuch")
    expect(ids).toContain("credentials")                              // Kern, immer da
  })

  it("blendet Bereiche ohne Freigabe aus", () => {
    const owners = { "/akte": "patientenakte", "/cryptoboard": "cryptoboard" }
    const access = user({ "module.patientenakte": false, "module.cryptoboard": true },
      ["module.patientenakte", "module.cryptoboard"])
    const ids = visibleVaultAreas(owners, access).map((a) => a.id)
    expect(ids).not.toContain("akte")
    expect(ids).toContain("cryptoboard")
  })

  it("kennt die vier Vault-Bereiche mit echten Pfaden", () => {
    const paths = Object.fromEntries(VAULT_AREAS.map((a) => [a.id, a.path]))
    expect(paths).toEqual({ akte: "/akte", cryptoboard: "/cryptoboard", haushaltsbuch: "/haushaltsbuch", credentials: "/credentials" })
  })

  it("nennt kein Scratchpad (nicht sensibel, kein Vault-Modul)", () => {
    expect(VAULT_AREAS.map((a) => a.path)).not.toContain("/scratchpad")
  })
})
