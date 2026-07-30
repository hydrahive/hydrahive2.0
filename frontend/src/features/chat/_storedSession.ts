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
