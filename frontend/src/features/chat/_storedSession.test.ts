// Task 8fd82c02: Projekt-Merker – eingebettete Chats (metadata.embedded_in) werden nie gemerkt.
import { beforeEach, describe, expect, it } from "vitest"
import { forgetDeleted, readStoredSession, rememberActive, writeStoredSession } from "./_storedSession"
import type { Session } from "./types"

const sess = (id: string, agent: string, metadata: Record<string, unknown> = {}): Session => ({
  id, agent_id: agent, user_id: "u", project_id: "p", title: id, status: "active", created_at: "", updated_at: "", metadata,
})

const mem = new Map<string, string>()
beforeEach(() => {
  mem.clear()
  Object.defineProperty(globalThis, "sessionStorage", { configurable: true, value: {
    getItem: (k: string) => mem.get(k) ?? null, setItem: (k: string, v: string) => { mem.set(k, v) },
  } })
})

describe("rememberActive", () => {
  it("merkt eine normale Sitzung je Projekt", () => {
    rememberActive("p1", sess("s1", "A"))
    expect(readStoredSession("p1")).toBe("s1")
  })
  it("eingebettete Sitzung: Merker des Projekts bleibt unberührt", () => {
    rememberActive("p1", sess("eigen", "A"))
    rememberActive("p1", sess("buch", "A", { embedded_in: "storyteller" }))
    expect(readStoredSession("p1")).toBe("eigen")
  })
  it("ohne Projekt-Kontext (undefined) oder unbekannte Sitzung: nichts", () => {
    rememberActive(undefined, sess("s1", "A"))
    rememberActive("p1", undefined)
    expect(mem.size).toBe(0)
  })
})

describe("forgetDeleted", () => {
  it("entfernt den Merker nur, wenn er auf die gelöschte Sitzung zeigt", () => {
    writeStoredSession("p1", "eigen")
    forgetDeleted("p1", "buch")
    expect(readStoredSession("p1")).toBe("eigen")
    forgetDeleted("p1", "eigen")
    expect(readStoredSession("p1")).toBeNull()
  })
  it("ohne Projekt-Kontext: nichts", () => {
    writeStoredSession("p1", "eigen")
    forgetDeleted(undefined, "eigen")
    expect(readStoredSession("p1")).toBe("eigen")
  })
})
