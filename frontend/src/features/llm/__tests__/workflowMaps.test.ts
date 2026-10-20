import { describe, expect, it } from "vitest"
import { workflowMaps } from "../workflowMaps"

describe("workflowMaps (Vorlagen für lokale Bild-Workflows)", () => {
  it("leere Platzhalter fallen weg, Verbindungen nur für gesetzte Vorlagen", () => {
    expect(workflowMaps({ prompt: "4.inputs.text", seed: "", reference_1: "10.inputs.image", reference_2: "" },
      { reference_1: "13.inputs.latent", reference_2: "23.inputs.latent" }))
      .toEqual({ placeholders: { prompt: "4.inputs.text", reference_1: "10.inputs.image" },
                 reference_links: { reference_1: "13.inputs.latent" } })
  })
  it("ohne Vorlagen kein reference_links-Feld", () => {
    expect(workflowMaps({ prompt: "6.inputs.text" }, {})).toEqual({ placeholders: { prompt: "6.inputs.text" } })
    expect(workflowMaps({ prompt: "6.inputs.text" }, { reference_1: "13.inputs.latent" })).toEqual({ placeholders: { prompt: "6.inputs.text" } })
  })
})
