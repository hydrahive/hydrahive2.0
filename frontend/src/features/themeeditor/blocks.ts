/** Baustein-Katalog für den GrapesJS-Theme-Editor.
 *
 *  Spiegelt das <hh-…/>-Inventar aus features/themetemplates/registry.tsx als
 *  editierbare Bausteine. Jeder Eintrag wird im Editor zu:
 *   - einem Custom Component Type (Import/Export erhält Tag + Attribute)
 *   - einem Palette-Block (Drag-Quelle)
 *   - einem sichtbaren Canvas-Platzhalter (man SIEHT den Baustein beim Bauen)
 *
 *  attrs = am Baustein editierbare Attribute (werden zu GrapesJS-Traits).
 */
export interface HhBlockDef {
  tag: string
  label: string
  category: string
  attrs: { name: string; default?: string }[]
}

export const HH_BLOCKS: HhBlockDef[] = [
  // Navigation
  { tag: "hh-menu", label: "Menü", category: "Navigation", attrs: [{ name: "type", default: "horizontal" }] },
  // Seiten (Chat-artige haben eine Höhe)
  { tag: "hh-buddy", label: "Buddy", category: "Seiten", attrs: [{ name: "height", default: "62vh" }] },
  { tag: "hh-werkstatt", label: "Werkstatt", category: "Seiten", attrs: [{ name: "height", default: "64vh" }] },
  { tag: "hh-teamchat", label: "Teamchat", category: "Seiten", attrs: [{ name: "height", default: "64vh" }] },
  { tag: "hh-butler", label: "Butler", category: "Seiten", attrs: [{ name: "height", default: "64vh" }] },
  { tag: "hh-communication", label: "Kommunikation", category: "Seiten", attrs: [] },
  { tag: "hh-atelier", label: "Atelier", category: "Seiten", attrs: [] },
  { tag: "hh-dashboard", label: "Dashboard", category: "Seiten", attrs: [] },
  { tag: "hh-memory", label: "Gedächtnis", category: "Seiten", attrs: [] },
  { tag: "hh-skills", label: "Skills", category: "Seiten", attrs: [] },
  { tag: "hh-datamining", label: "Datamining", category: "Seiten", attrs: [] },
  { tag: "hh-vms", label: "VMs", category: "Seiten", attrs: [] },
  { tag: "hh-containers", label: "Container", category: "Seiten", attrs: [] },
  { tag: "hh-federation", label: "Föderation", category: "Seiten", attrs: [] },
  { tag: "hh-streaming", label: "Streaming", category: "Seiten", attrs: [] },
  { tag: "hh-mcp", label: "MCP-Server", category: "Seiten", attrs: [] },
  { tag: "hh-zahnfee", label: "Zahnfee", category: "Seiten", attrs: [] },
  // Status-Karten
  { tag: "hh-tailscale", label: "Tailscale", category: "Karten", attrs: [] },
  { tag: "hh-agentlink", label: "AgentLink", category: "Karten", attrs: [] },
  { tag: "hh-minimax", label: "Minimax-Usage", category: "Karten", attrs: [] },
]

/** Ein Attribut-String für einen Palette-Block, z.B. ' type="horizontal"'. */
export function defaultAttrString(def: HhBlockDef): string {
  return def.attrs
    .filter((a) => a.default)
    .map((a) => ` ${a.name}="${a.default}"`)
    .join("")
}
