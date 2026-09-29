// Welche Werkzeuge darf der Besitzer eines Agenten nicht nutzen? (access-groups §9)
// Nur Anzeige: durchgesetzt wird im Backend (Runner-Filter + Dispatcher).
import type { MyAccess } from "./types"

interface ToolWithCapability {
  name: string
  capability?: string | null
}

export function blockedTools(tools: ToolWithCapability[], access: MyAccess | null): Set<string> {
  const out = new Set<string>()
  if (!access || access.admin) return out
  const declared = new Set(access.declared)
  for (const tool of tools) {
    const cap = tool.capability
    if (cap && declared.has(cap) && !access.capabilities[cap]) out.add(tool.name)
  }
  return out
}
