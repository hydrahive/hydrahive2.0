// docs/specs/chat-mobile-compact.md: Die Fußzeile öffnet den Hilfe-Assistenten über ein Ereignis,
// weil der schwebende Knopf auf dem Handy Chat-Knöpfe überdeckte (Task 37232294).
// Die Tests laufen ohne Browser (node): window wird durch ein EventTarget ersetzt.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "TOK" }) } }))
import { HELP_TOGGLE_EVENT, requestHelpToggle } from "./helpApi"

describe("requestHelpToggle", () => {
  let target: EventTarget
  beforeEach(() => { target = new EventTarget(); vi.stubGlobal("window", target) })
  afterEach(() => vi.unstubAllGlobals())

  it("hat einen festen, eindeutigen Ereignisnamen", () => {
    expect(HELP_TOGGLE_EVENT).toBe("hh:help-toggle")
  })

  it("schickt genau ein Ereignis an window", () => {
    const seen: string[] = []
    target.addEventListener(HELP_TOGGLE_EVENT, (e) => seen.push(e.type))
    requestHelpToggle()
    expect(seen).toEqual(["hh:help-toggle"])
  })

  it("wirft nicht, wenn es kein window gibt", () => {
    vi.stubGlobal("window", undefined)
    expect(() => requestHelpToggle()).not.toThrow()
  })
})
