import { isEmbedded } from "./_pickSession"
import type { Session } from "./types"

const STORAGE_KEY = "hh.cockpit.activeSession"

/**
 * Merkt sich die zuletzt geöffnete Session pro Projekt — damit ein F5 nicht in
 * einem anderen Chat landet.
 *
 * Ergänzt die persistente Agenten-Auswahl: hat ein Agent mehrere Sessions,
 * würde man sonst nach dem Reload in seiner NEUESTEN statt in der zuletzt
 * offenen landen.
 *
 * Bewusst sessionStorage statt User-Preferences: die Auswahl ist Tab-lokal.
 * Zwei Tabs mit verschiedenen Sessions desselben Projekts dürfen sich nicht
 * gegenseitig umschalten, und ein Serverabgleich wäre dafür unnötig.
 */
export function readStoredSession(projectId: string | null): string | null {
  if (!projectId) return null
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return (JSON.parse(raw) as Record<string, string>)[projectId] ?? null
  } catch {
    return null
  }
}

/** Offene Sitzung als Projekt-Merker speichern – nur mit Projekt (ohne Projekt tut writeStoredSession nichts)
 *  und nie für eingebettete Chats (z. B. Storyteller-Fenster): sonst öffnet das
 *  Cockpit danach deren Sitzung. Unbekannte Sitzung (nicht in der Liste) wird nicht gemerkt – sie wäre beim
 *  nächsten Laden ohnehin nicht wählbar. */
export function rememberActive(projectId: string | null | undefined, session: Session | undefined): void {
  if (session && !isEmbedded(session)) writeStoredSession(projectId ?? null, session.id)
}

/** Merker entfernen, wenn er auf die gelöschte Sitzung zeigt (andere Merker bleiben). */
export function forgetDeleted(projectId: string | null | undefined, sessionId: string): void {
  if (readStoredSession(projectId ?? null) === sessionId) writeStoredSession(projectId ?? null, null)
}

export function writeStoredSession(projectId: string | null, sessionId: string | null): void {
  if (!projectId) return
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    const map = raw ? (JSON.parse(raw) as Record<string, string>) : {}
    if (sessionId) map[projectId] = sessionId
    else delete map[projectId]
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(map))
  } catch {
    // Privater Modus / Speicher voll: Persistenz entfällt, Funktion bleibt.
  }
}
