/** Reine Logik der Template-Seite (ohne React), getestet in templateLogic.test.ts. */
import type { AgentTemplate, TemplateBody, TemplateGroup } from "./types"

export const GROUP_ORDER: TemplateGroup[] = ["personal", "projects", "specialists", "modules", "system"]
export const CHAIN_STEPS = 3
const ID = /^[a-z][a-z0-9-]{1,40}$/

/** Templates nach Gruppe, in fester Gruppenreihenfolge, innerhalb alphabetisch. */
export function groupTemplates(list: AgentTemplate[]): { group: TemplateGroup; items: AgentTemplate[] }[] {
  return GROUP_ORDER
    .map((group) => ({
      group,
      items: list.filter((t) => t.group === group).sort((a, b) => a.label.localeCompare(b.label)),
    }))
    .filter((g) => g.items.length > 0)
}

/** Anbieter einer Modell-ID, grob – nur für die Warnung „gleicher Anbieter“. */
export function providerOf(model: string): string {
  if (!model) return ""
  if (model.startsWith("openai-codex/")) return "openai-codex"
  if (model.includes("/")) return model.split("/")[0]
  if (model.startsWith("claude")) return "anthropic"
  if (model.toLowerCase().includes("minimax")) return "minimax"
  return model
}

export function sameProviderSteps(chain: string[]): boolean {
  const p = chain.filter(Boolean).map(providerOf)
  return new Set(p).size < p.length
}

/** Kette auf genau CHAIN_STEPS Felder (für die drei Auswahlfelder). */
export function padChain(chain: string[]): string[] {
  return [...chain, "", "", ""].slice(0, CHAIN_STEPS)
}

/** Leere Stufen entfernen; Reihenfolge bleibt. */
export function compactChain(chain: string[]): string[] {
  return chain.map((m) => m.trim()).filter(Boolean)
}

export function toBody(t: AgentTemplate): TemplateBody {
  return {
    label: t.label, group: t.group, chain: compactChain(t.chain), failover_on: [...t.failover_on],
    budget: { ...t.budget }, reply: { ...t.reply }, on_demand: t.on_demand, description: t.description,
  }
}

export function isValidId(id: string): boolean {
  return ID.test(id)
}

/** Budget mit erlaubter Überschreitung (für die Anzeige „bis zu …“). */
export function withOverrun(value: number, pct: number): number {
  return Math.floor(value * (1 + Math.max(0, pct) / 100))
}

export function newTemplate(id: string, base?: AgentTemplate): AgentTemplate {
  return {
    id, label: id, group: base?.group ?? "specialists", chain: base ? [...base.chain] : [],
    failover_on: base ? [...base.failover_on] : ["auth", "quota", "rate_limit", "overload", "timeout", "stream_abort", "empty"],
    budget: base ? { ...base.budget } : {
      max_iterations: 32, max_tokens: 16384, timeout_seconds: 540, compact_threshold_pct: 75,
      overrun_pct: 20, cooldown_seconds: 300, reasoning_effort: "", cache_ttl: "1h",
    },
    reply: base ? { ...base.reply } : { summary_max_chars: 2000, full_report: "file" },
    on_demand: false, description: "", revision: 0,
  }
}
