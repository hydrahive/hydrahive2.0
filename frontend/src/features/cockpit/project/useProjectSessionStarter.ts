import { useState } from "react"
import { chatApi } from "@/features/chat/api"

/**
 * Startet eine neue Projekt-Session mit einem EXPLIZIT gewählten Agenten.
 *
 * Abgrenzung zum „Neuer Chat"-Button im Chat-Header: der nimmt den Agenten der
 * gerade offenen Session. Hier wählt der Nutzer den Agenten bewusst im
 * Projekt-Team-Panel — diese Wahl darf nicht überschrieben werden.
 *
 * Vor dem Anlegen wird die laufende Projekt-Session übergeben (handover), damit
 * der Kontext nicht verloren geht. Serverseitig ist handover ohne Projekt ein
 * No-Op, deshalb ist der Aufruf gefahrlos.
 */
export function useProjectSessionStarter(projectId: string | null) {
  const [pendingAgentId, setPendingAgentId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function start(agentId: string): Promise<string | null> {
    // Guard gegen Doppelklick: sonst zwei Sessions + zwei Handover-Läufe.
    if (!projectId || pendingAgentId) return null
    setPendingAgentId(agentId)
    setError(null)
    try {
      const sessions = await chatApi.listSessions()
      const current = sessions
        .filter((s) => s.project_id === projectId)
        .sort((a, b) => b.created_at.localeCompare(a.created_at))[0]
      if (current) await chatApi.handover(current.id)
      const created = await chatApi.createSession(agentId, undefined, projectId)
      return created.id
    } catch {
      setError("Neue Session konnte nicht gestartet werden.")
      return null
    } finally {
      setPendingAgentId(null)
    }
  }

  return { start, pendingAgentId, error, clearError: () => setError(null) }
}
