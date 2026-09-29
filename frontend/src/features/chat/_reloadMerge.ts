import type { Message } from "./types"

/** Nachrichten im Chat-State plus die Session, zu der sie gehören. */
export interface LoadedThread {
  messages: Message[]
  loadedFor: string | null
}

function isPlaceholder(m: Message): boolean {
  return m.id.startsWith("local-") || m.id.startsWith("live-")
}

/**
 * Führt einen Reload mit dem aktuellen Thread zusammen.
 *
 * Lokale Platzhalter (`local-` = abgeschickte Nachricht, `live-` = Live-Antwort)
 * haben nie die ID, unter der der Server sie speichert — ein ID-Abgleich findet
 * sie deshalb nie wieder. Sie bleiben darum nur stehen, solange ein Lauf aktiv
 * ist UND dieselbe Session nachgeladen wird (#437: ein Live-Sync-Reload mitten
 * im Lauf darf die gerade abgeschickte Nachricht nicht wegwischen). Danach gilt
 * der Serverstand; sonst stünde jede Antwort doppelt da und die Platzhalter
 * wanderten beim Session-Wechsel in die nächste Session mit.
 */
export function applyReload(
  current: LoadedThread,
  sessionId: string,
  fromServer: Message[],
  runActive: boolean,
): LoadedThread {
  const sameSession = current.loadedFor === sessionId
  const pending = runActive && sameSession ? current.messages.filter(isPlaceholder) : []
  return { messages: [...fromServer, ...pending], loadedFor: sessionId }
}
