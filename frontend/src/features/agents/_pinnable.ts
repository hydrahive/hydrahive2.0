import type { Agent, ToolMeta } from "./types"

/** Anheftbar ist nur, was der Agent selbst hat (Tools oder kategorie:x); anderes wirkt im Lauf still nicht (Review #788). */
export function pinnable(draft: Agent, tools: ToolMeta[]): ToolMeta[] {
  const own = new Set(draft.tools ?? [])
  const cats = new Set((draft.tools ?? []).filter((n) => n.startsWith("kategorie:")).map((n) => n.slice(10)))
  const pinned = new Set(draft.pinned_tools ?? [])
  return tools.filter((tool) => own.has(tool.name) || cats.has(tool.category ?? "other") || pinned.has(tool.name))
}
