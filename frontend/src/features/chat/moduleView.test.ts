import { describe, expect, it } from "vitest"
import { mediaFromBlocks } from "./MediaPreview"
import { FRAME_SANDBOX, isSandboxUrl, viewLinkPath } from "./moduleView"

describe("module_view (Spec module-view-sandbox §2.3)", () => {
  it("mediaFromBlocks reicht module_view durch", () => {
    const m = mediaFromBlocks([{ kind: "module_view", module: "diagramme", view_id: "d1", title: "Websuche" }])
    expect(m.views).toEqual([{ module: "diagramme", view_id: "d1", title: "Websuche" }])
    expect(m.images).toEqual([])
  })

  it("ohne module_view bleibt views leer", () => {
    expect(mediaFromBlocks([{ kind: "image", url: "https://x/y.png" }]).views).toEqual([])
    expect(mediaFromBlocks(undefined).views).toEqual([])
  })

  it("view-link-Pfad nur für gültige Modul- und Ansichts-IDs", () => {
    expect(viewLinkPath("diagramme", "d_1-A")).toBe("/modules/diagramme/view-link/d_1-A")
    expect(viewLinkPath("../x", "d1")).toBeNull()
    expect(viewLinkPath("Diagramme", "d1")).toBeNull()
    expect(viewLinkPath("diagramme", "a/b")).toBeNull()
    expect(viewLinkPath("diagramme", "x".repeat(65))).toBeNull()
  })

  it("nur relative Sandbox-Adressen des eigenen Moduls werden geladen", () => {
    expect(isSandboxUrl("diagramme", "/api/module-device/diagramme/sandbox/d1?exp=1&sig=ab")).toBe(true)
    expect(isSandboxUrl("diagramme", "/api/module-device/mining/sandbox/d1")).toBe(false)
    expect(isSandboxUrl("diagramme", "https://evil.example/api/module-device/diagramme/sandbox/d1")).toBe(false)
    expect(isSandboxUrl("diagramme", "//evil.example/api/module-device/diagramme/sandbox/d1")).toBe(false)
    expect(isSandboxUrl("diagramme", "/api/module-device/diagramme/sandbox/../../files")).toBe(false)
    expect(isSandboxUrl("diagramme", "/api/modules/diagramme/sandbox/d1")).toBe(false)
    expect(isSandboxUrl("diagramme", 42 as unknown as string)).toBe(false)
  })

  it("Rahmen-Rechte exakt, nie same-origin, top-navigation oder forms", () => {
    expect(FRAME_SANDBOX).toBe("allow-scripts allow-popups allow-popups-to-escape-sandbox")
    for (const bad of ["allow-same-origin", "allow-top-navigation", "allow-forms"]) expect(FRAME_SANDBOX).not.toContain(bad)
  })
})
