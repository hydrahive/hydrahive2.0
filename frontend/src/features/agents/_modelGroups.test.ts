import { describe, expect, it } from "vitest"
import type { RegistryModel } from "@/features/llm/api"
import { groupModels, providersOf } from "./_modelGroups"

function m(id: string, provider: string, is_free: boolean | null = null, label?: string): RegistryModel {
  return { id, label: label ?? id, provider, purposes: ["chat"], context_window: null, is_free, embed_dim: null }
}

// Nachbau der echten Lage (30.09.2026): viele Modelle vorne, Codex/OpenRouter hinten.
const catalog: RegistryModel[] = [
  ...Array.from({ length: 13 }, (_, i) => m(`claude-${i}`, "anthropic")),
  ...Array.from({ length: 73 }, (_, i) => m(`nvidia/model-${i}`, "nvidia")),
  m("ollama/llama3", "ollama", true),
  ...Array.from({ length: 128 }, (_, i) => m(`openai/gpt-${i}`, "openai")),
  ...Array.from({ length: 14 }, (_, i) => m(`openai-codex/gpt-5.${i}`, "openai-codex")),
  ...Array.from({ length: 465 }, (_, i) => m(`openrouter/vendor/model-${i}`, "openrouter", i % 5 === 0)),
]
const all = { query: "", onlyFree: false, provider: "" }
const flat = (groups: ReturnType<typeof groupModels>) => groups.flatMap((g) => g.models)

describe("groupModels", () => {
  it("bietet ohne Filter aus jedem Anbieter mindestens ein Modell an (Task 19687316)", () => {
    const groups = groupModels(catalog, all)
    const providers = new Set(catalog.map((x) => x.provider))
    for (const p of providers) {
      expect(groups.find((g) => g.provider === p)?.models.length ?? 0).toBeGreaterThan(0)
    }
  })

  it("lässt kein Modell weg, auch nicht über 100", () => {
    expect(flat(groupModels(catalog, all))).toHaveLength(catalog.length)
    expect(flat(groupModels(catalog, all)).some((x) => x.id === "openai-codex/gpt-5.13")).toBe(true)
  })

  it("sortiert Gruppen nach Anzeigename und Modelle nach id", () => {
    const groups = groupModels([m("b", "openrouter"), m("a", "openrouter"), m("z", "anthropic")], all)
    expect(groups.map((g) => g.provider)).toEqual(["anthropic", "openrouter"])
    expect(groups[1].models.map((x) => x.id)).toEqual(["a", "b"])
    expect(groups[1].name).toBe("OpenRouter")
  })

  it("filtert nach Anbieter", () => {
    const groups = groupModels(catalog, { ...all, provider: "openai-codex" })
    expect(groups.map((g) => g.provider)).toEqual(["openai-codex"])
    expect(groups[0].models).toHaveLength(14)
  })

  it("sucht in id und Label, ohne Groß/klein", () => {
    const list = [m("x/one", "openrouter", null, "Super Modell"), m("x/two", "openrouter")]
    expect(flat(groupModels(list, { ...all, query: "SUPER" })).map((x) => x.id)).toEqual(["x/one"])
    expect(flat(groupModels(list, { ...all, query: "TWO" })).map((x) => x.id)).toEqual(["x/two"])
  })

  it("filtert nur gratis, auch zusammen mit Anbieter und Suche", () => {
    const free = flat(groupModels(catalog, { ...all, onlyFree: true }))
    expect(free.every((x) => x.is_free === true)).toBe(true)
    const combo = flat(groupModels(catalog, { query: "model-10", onlyFree: true, provider: "openrouter" }))
    // gratis = Index durch 5 teilbar; "model-10" trifft 10, 100–109 → gratis davon: 10, 100, 105
    expect(combo.map((x) => x.id)).toEqual([
      "openrouter/vendor/model-10", "openrouter/vendor/model-100", "openrouter/vendor/model-105",
    ])
  })

  it("begrenzt auch die Zahl der Anbieter-Gruppen nicht", () => {
    const many = Array.from({ length: 120 }, (_, i) => m(`p${i}/x`, `p${String(i).padStart(3, "0")}`))
    expect(groupModels(many, all)).toHaveLength(120)
  })

  it("liefert eine leere Liste, wenn nichts passt", () => {
    expect(groupModels(catalog, { ...all, query: "gibtesnicht" })).toEqual([])
  })
})

describe("providersOf", () => {
  it("zählt je Anbieter und sortiert nach Anzeigename", () => {
    const list = providersOf(catalog)
    expect(list.find((p) => p.provider === "openrouter")?.count).toBe(465)
    expect(list.find((p) => p.provider === "openai-codex")?.name).toBe("ChatGPT Plus/Pro (Codex)")
    expect(list.map((p) => p.name)).toEqual([...list.map((p) => p.name)].sort((a, b) => a.localeCompare(b)))
  })
})
