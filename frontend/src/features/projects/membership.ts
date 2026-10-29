import type { Project } from "./types"

/** Ist `username` Mitglied (oder Ersteller) des Projekts? Spiegel von
 *  core projects/_members_model.role_of: created_by zählt immer, Mitglieder
 *  stehen als { username, role } oder im alten Format als reiner Name. */
export function isProjectMember(project: Pick<Project, "created_by" | "members">, username: string | null | undefined): boolean {
  if (!username) return false
  if (project.created_by === username) return true
  const members = (project.members ?? []) as unknown[]
  return members.some((m) => (typeof m === "string" ? m : (m as { username?: string })?.username) === username)
}

/** Nur die Projekte, in denen `username` Mitglied ist (Reihenfolge bleibt).
 *  System-Admins bekommen von /api/projects ALLE Projekte – Module wie Atelier und
 *  Studio arbeiten aber nur mit Projekten, in denen man Mitglied ist. */
export function ownProjects<T extends Pick<Project, "created_by" | "members">>(projects: T[], username: string | null | undefined): T[] {
  return projects.filter((p) => isProjectMember(p, username))
}
