import type { Session } from "./types"

/** Vereint überlappende API-Seiten; die neu geladene Version einer Session gewinnt. */
export function mergeSessionPages(existing: Session[], incoming: Session[]): Session[] {
  const sessions = new Map(existing.map((session) => [session.id, session]))
  for (const session of incoming) sessions.set(session.id, session)

  return [...sessions.values()].sort((a, b) =>
    b.updated_at.localeCompare(a.updated_at) || b.id.localeCompare(a.id),
  )
}

/** undefined = alle, null = ohne Projekt, string = genau dieses Projekt. */
export function sessionMatchesScope(session: Session, projectId?: string | null): boolean {
  if (projectId === undefined) return true
  return session.project_id === projectId
}
