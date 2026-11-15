import { describe, expect, it } from "vitest"
import { canSaveAgent } from "./projectAgentEditGuards"

const BASE = { dirty: true, saving: false, deleteStarted: false, name: "Agent", llmModel: "modell-a", promptDirty: false, prompt: "" }

describe("canSaveAgent", () => {
  it("erlaubt Speichern bei gültigem, geändertem Entwurf", () => {
    expect(canSaveAgent(BASE)).toBe(true)
  })

  it("sperrt Speichern, solange ein Lösch-Auftrag für den Agenten läuft oder lief", () => {
    // Grund: ein PATCH könnte sonst status:\"active\" zurückschreiben und die Sperre
    // aus dem Lösch-Auftrag (Backend _lock.py) aufheben.
    expect(canSaveAgent({ ...BASE, deleteStarted: true })).toBe(false)
  })

  it("sperrt ohne Änderungen", () => {
    expect(canSaveAgent({ ...BASE, dirty: false })).toBe(false)
  })

  it("sperrt während ein Speichern läuft", () => {
    expect(canSaveAgent({ ...BASE, saving: true })).toBe(false)
  })

  it("sperrt bei leerem Namen oder Modell", () => {
    expect(canSaveAgent({ ...BASE, name: "   " })).toBe(false)
    expect(canSaveAgent({ ...BASE, llmModel: "" })).toBe(false)
  })

  it("sperrt bei geändertem, aber leerem Prompt", () => {
    expect(canSaveAgent({ ...BASE, promptDirty: true, prompt: "  " })).toBe(false)
    expect(canSaveAgent({ ...BASE, promptDirty: true, prompt: "neuer Prompt" })).toBe(true)
  })
})
