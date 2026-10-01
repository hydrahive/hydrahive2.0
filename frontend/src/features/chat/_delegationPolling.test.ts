import { describe, expect, it } from "vitest"
import { AFTER_RUN_GRACE_MS, isRefreshPing, shouldPoll } from "./_delegationPolling"

const base = { hasSession: true, running: 0, busy: false, runEndedAt: null, now: 100_000 }

describe("shouldPoll", () => {
  it("fragt ab, solange ein Auftrag läuft oder ein eigener Lauf aktiv ist", () => {
    expect(shouldPoll({ ...base, running: 1 })).toBe(true)
    expect(shouldPoll({ ...base, busy: true })).toBe(true)
  })

  it("fragt nach Lauf-Ende noch eine Weile weiter (ask_agent als letzte Aktion)", () => {
    // Befund 01.10.2026: Der Auftrag kam erst nach der letzten Abfrage an,
    // danach wurde nie wieder gefragt → Leiste nur nach F5 sichtbar.
    expect(shouldPoll({ ...base, runEndedAt: base.now - 1000 })).toBe(true)
    expect(shouldPoll({ ...base, runEndedAt: base.now - AFTER_RUN_GRACE_MS + 1 })).toBe(true)
  })

  it("hört danach auf, wenn nichts läuft", () => {
    expect(shouldPoll({ ...base, runEndedAt: base.now - AFTER_RUN_GRACE_MS - 1 })).toBe(false)
    expect(shouldPoll(base)).toBe(false)
  })

  it("ohne Session nie", () => {
    expect(shouldPoll({ ...base, hasSession: false, running: 2, busy: true })).toBe(false)
  })
})

describe("isRefreshPing", () => {
  it("lädt bei Lauf-Start und -Ende sofort neu, nicht bei jedem Fortschritts-Ping", () => {
    expect(isRefreshPing("start")).toBe(true)
    expect(isRefreshPing("done")).toBe(true)
    expect(isRefreshPing("activity")).toBe(false)
    expect(isRefreshPing("")).toBe(false)
  })
})
