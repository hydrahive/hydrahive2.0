/**
 * Wissensräume (docs/specs/knowledge-spaces.md): Einstellung `knowledge_access` eines Agenten.
 * Reine Logik ohne React – getestet in knowledgeAccess.test.ts.
 */

export type KnowledgeLevel = "normal" | "privat" | "gesundheit"
export const LEVELS: KnowledgeLevel[] = ["normal", "privat", "gesundheit"]

export interface KnowledgeAccess {
  scope?: "project" | "user"
  projects?: string[]
  groups?: string[]
  max_level?: KnowledgeLevel
  sensitive?: boolean          // E0-Altfeld, wird beim Speichern durch max_level ersetzt
}

export interface KnowledgeInfo {
  settings: KnowledgeAccess
  effective: { scope: "project" | "user"; projects: string[]; max_level: KnowledgeLevel; group_users: string[] }
  limited_by_outward_tools: boolean
  outward_tools: string[]
  counted_for: string
  visible_events: number | null
}

/** Wert für den Stufen-Regler: max_level, sonst Altfeld sensitive, sonst Standard je Typ. */
export function levelOf(ka: KnowledgeAccess | undefined, agentType: string): KnowledgeLevel {
  if (ka?.max_level && LEVELS.includes(ka.max_level)) return ka.max_level
  if (ka?.sensitive === true) return "gesundheit"
  if (ka?.sensitive === false) return "normal"
  return agentType === "master" ? "gesundheit" : "normal"
}

/** Standard je Typ – entspricht db/_mirror_scope.defaults_for. */
export function defaultsFor(agentType: string): Required<Pick<KnowledgeAccess, "scope" | "max_level">> {
  return agentType === "master" ? { scope: "user", max_level: "gesundheit" } : { scope: "project", max_level: "normal" }
}

/**
 * Aus den Eingaben die zu speichernde Einstellung bauen. Nur Abweichungen vom Standard werden
 * gespeichert; nichts abweichend → `{}` (Server entfernt das Feld = Standard je Typ).
 * Das Altfeld `sensitive` fällt dabei weg.
 */
export function buildAccess(
  agentType: string,
  v: { scope: "project" | "user"; projects: string[]; groups: string[]; max_level: KnowledgeLevel },
): KnowledgeAccess {
  const d = defaultsFor(agentType)
  const out: KnowledgeAccess = {}
  if (v.scope !== d.scope) out.scope = v.scope
  if (v.max_level !== d.max_level) out.max_level = v.max_level
  const projects = [...new Set(v.projects.filter(Boolean))]
  const groups = [...new Set(v.groups.filter(Boolean))]
  if (projects.length) out.projects = projects
  if (groups.length) out.groups = groups
  return out
}

/** Gleicher Inhalt? (Reihenfolge der Listen egal) – für „ungespeicherte Änderung“. */
export function sameAccess(a: KnowledgeAccess | undefined, b: KnowledgeAccess | undefined): boolean {
  const norm = (k?: KnowledgeAccess) => JSON.stringify({
    scope: k?.scope ?? null, max_level: k?.max_level ?? null, sensitive: k?.sensitive ?? null,
    projects: [...(k?.projects ?? [])].sort(), groups: [...(k?.groups ?? [])].sort(),
  })
  return norm(a) === norm(b)
}
