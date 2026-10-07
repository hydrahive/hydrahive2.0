// Task 8fd82c02: Sitzungen eingebetteter Chats (z. B. Storyteller-Chatfenster, metadata.embedded_in) öffnet das
// Projekt-Cockpit nie von selbst – weder als „neueste Sitzung“ noch über einen (alten) Merker.
import { describe, expect, it } from "vitest"
import { pickSessionFor } from "./_pickSession"
import type { Session } from "./types"

const sess = (id: string, agent: string, metadata: Record<string, unknown> = {}): Session => ({
  id, agent_id: agent, user_id: "u", project_id: "p", title: id, status: "active", created_at: "", updated_at: "", metadata,
})

describe("pickSessionFor – eingebettete Sitzungen", () => {
  const list = [sess("buch", "A", { embedded_in: "storyteller" }), sess("eigen", "A"), sess("spezial", "B")]

  it("überspringt die neueste, wenn sie eingebettet ist (mit bevorzugtem Agenten)", () => {
    expect(pickSessionFor(list, "A")).toBe("eigen")
  })
  it("überspringt sie auch ohne bevorzugten Agenten", () => {
    expect(pickSessionFor(list, null)).toBe("eigen")
  })
  it("ein alter Merker auf die eingebettete Sitzung zählt nicht", () => {
    expect(pickSessionFor(list, "A", "buch")).toBe("eigen")
    expect(pickSessionFor(list, null, "buch")).toBe("eigen")
  })
  it("hat der Agent nur eingebettete Sitzungen → null (Leerzustand statt Buch-Chat)", () => {
    expect(pickSessionFor([sess("buch", "A", { embedded_in: "storyteller" }), sess("x", "B")], "A")).toBeNull()
  })
  it("nur eingebettete Sitzungen und kein bevorzugter Agent → null", () => {
    expect(pickSessionFor([sess("buch", "A", { embedded_in: "storyteller" })], null)).toBeNull()
  })
  it("leerer oder fehlerhafter Wert zählt nicht als eingebettet", () => {
    expect(pickSessionFor([sess("a", "A", { embedded_in: "" }), sess("b", "A")], "A")).toBe("a")
    expect(pickSessionFor([sess("a", "A", { embedded_in: 1 }), sess("b", "A")], "A")).toBe("a")
    expect(pickSessionFor([{ ...sess("a", "A"), metadata: undefined as unknown as Record<string, unknown> }, sess("b", "A")], "A")).toBe("a")
  })
  it("altes Verhalten ohne eingebettete Sitzungen unverändert (Merker, neueste, Agent)", () => {
    expect(pickSessionFor([sess("n", "A"), sess("o", "B")], null)).toBe("n")
    expect(pickSessionFor([sess("n", "A"), sess("o", "B")], "B")).toBe("o")
    expect(pickSessionFor([sess("n", "A"), sess("o", "A")], "A", "o")).toBe("o")
    expect(pickSessionFor([], "A")).toBeNull()
  })
})
