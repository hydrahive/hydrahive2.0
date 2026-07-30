import type { Session } from "./types"

/**
 * Wählt die Session, die beim (Neu-)Laden geöffnet wird.
 *
 * Mit bevorzugtem Agenten (Projekt-Cockpit: der links angeklickte) gewinnt
 * dessen NEUESTE eigene Session. Ohne diese Filterung landete jeder Klick in
 * der neuesten Session des Projekts — bei gemischten Sessions (Projekt-Agent
 * + Spezialisten) also immer im selben Chat, egal wen man anklickt.
 *
 * Hat der Agent noch keine Session, wird bewusst `null` zurückgegeben: der
 * Chat zeigt dann den Leerzustand mit „Session mit <Agent> starten“, statt
 * einen fremden Agenten zu öffnen.
 *
 * Ohne preferredAgentId bleibt das alte Verhalten (neueste Session) — die
 * normale Chat-Seite setzt die Prop nicht und ist damit unverändert.
 *
 * Erwartet die Liste vorsortiert nach updated_at DESC (so liefert sie
 * `list_for_user` in core/src/hydrahive/db/sessions.py).
 */
export function pickSessionFor(
  sessions: Session[],
  preferredAgentId: string | null,
  rememberedId?: string | null,
  opts?: { agentExplicit?: boolean },
): string | null {
  if (sessions.length === 0) return null

  // Nach F5 die zuletzt offene Session wiederherstellen.
  //
  // Der Agent-Abgleich ist bewusst an `agentExplicit` gekoppelt: Nur wenn die
  // Agentenwahl WIRKLICH vom Nutzer stammt, darf ein abweichender Merker
  // verworfen werden (sonst zöge ein Agentenwechsel die alte Session wieder
  // auf). Stammt der Agent dagegen nur aus dem Fallback — etwa weil die
  // Preferences noch laden —, gewinnt der Merker: sonst verwirft ausgerechnet
  // die Schutzprüfung die korrekt gemerkte Session und öffnet den Chat des
  // Projekt-Agenten.
  if (rememberedId) {
    const remembered = sessions.find((s) => s.id === rememberedId)
    if (remembered) {
      const agentMismatch = Boolean(preferredAgentId) && remembered.agent_id !== preferredAgentId
      if (!agentMismatch || !opts?.agentExplicit) return remembered.id
    }
  }

  if (!preferredAgentId) return sessions[0].id
  const own = sessions.filter((s) => s.agent_id === preferredAgentId)
  return own.length > 0 ? own[0].id : null
}
