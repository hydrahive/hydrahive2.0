/**
 * Bausteine aus Modulen für den Butler-Editor (docs/specs/butler-module-nodes.md).
 *
 * Der Server liefert sie über GET /api/butler/registry mit Label, Beschreibung und ParamSchema. Die eingebauten
 * Bausteine bleiben in palette-data.ts; hier nur das, was Module beisteuern.
 */
import { useEffect, useState } from "react"
import { api } from "@/shared/api-client"

export type SchemaKind = "text" | "textarea" | "select" | "time" | "number" | "checkbox" | "list_text"

export interface SchemaParam {
  key: string
  label: string
  kind: SchemaKind | string
  required: boolean
  options: string[]
  placeholder: string | null
  default: unknown
}

export interface ModuleNode {
  type: "trigger" | "condition" | "action"
  subtype: string
  module: string
  label: string
  description: string
  params: SchemaParam[]
  implemented: boolean
}

const NODE_TYPE = { trigger: "triggerNode", condition: "conditionNode", action: "actionNode" } as const
const ORDER = ["trigger", "condition", "action"] as const

let cache: ModuleNode[] | null = null

/** Einmal laden; bei Fehler leere Liste – der Editor funktioniert dann wie bisher. */
export function useModuleNodes(): ModuleNode[] {
  const [nodes, setNodes] = useState<ModuleNode[]>(cache ?? [])
  useEffect(() => {
    if (cache) return
    void api.get<{ nodes: ModuleNode[] }>("/butler/registry")
      .then((r) => { cache = r.nodes ?? []; setNodes(cache) })
      .catch(() => { cache = []; setNodes([]) })
  }, [])
  return nodes
}

export function findModuleNode(nodes: ModuleNode[], subtype: string): ModuleNode | undefined {
  return nodes.find((n) => n.subtype === subtype)
}

export function moduleDefaults(node: ModuleNode): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const p of node.params) {
    if (p.default !== null && p.default !== undefined && p.default !== "") out[p.key] = p.default
  }
  return out
}

export interface PaletteGroup {
  type: (typeof NODE_TYPE)[keyof typeof NODE_TYPE]
  kind: (typeof ORDER)[number]
  items: { type: string; subtype: string; label: string; module: string; implemented: boolean }[]
}

export function paletteGroupsFor(nodes: ModuleNode[]): PaletteGroup[] {
  return ORDER.map((kind) => ({
    type: NODE_TYPE[kind], kind,
    items: nodes.filter((n) => n.type === kind)
      .map((n) => ({ type: NODE_TYPE[kind], subtype: n.subtype, label: n.label, module: n.module, implemented: n.implemented })),
  })).filter((g) => g.items.length > 0)
}

function show(v: unknown): string {
  if (Array.isArray(v)) return v.map(String).join(", ")
  if (typeof v === "boolean") return ""
  return v === null || v === undefined ? "" : String(v)
}

/** Kurzvorschau auf dem Knoten: die ersten zwei gesetzten Werte. */
export function moduleSummary(node: ModuleNode, params: Record<string, unknown>): string {
  return node.params.map((p) => show(params[p.key])).filter(Boolean).slice(0, 2).join(" · ")
}

/** Eingabe in den gespeicherten Wert umwandeln; undefined = Feld leeren. */
export function cleanSchemaValue(p: SchemaParam, raw: unknown): unknown {
  switch (p.kind) {
    case "number": {
      const n = typeof raw === "number" ? raw : Number(String(raw).trim())
      return String(raw).trim() !== "" && Number.isFinite(n) ? n : undefined
    }
    case "checkbox":
      return raw === true
    case "select":
      return p.options.includes(String(raw)) ? String(raw) : undefined
    case "list_text":
      return String(raw ?? "").split("\n").map((s) => s.trim()).filter(Boolean)
    default:
      return String(raw ?? "")
  }
}
