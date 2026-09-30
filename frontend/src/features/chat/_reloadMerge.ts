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

/** Fehler-Teil des Chat-States (siehe useChat). */
export interface ErrorSlice {
  loadedFor: string | null
  error: string | null
  errorKind: string | null
}

/**
 * Welcher Fehler nach einem erfolgreichen Reload stehen bleibt.
 *
 * Nach jedem Lauf pingt der Server (Live-Sync), das löst einen Reload aus.
 * Früher hat der Reload jeden Fehler außer max_iterations gelöscht; ein
 * Abbruch (refusal, leere Antwort, LLM-Fehler) war deshalb nur kurz oder gar
 * nicht zu sehen (Task 891f1d3a). Jetzt bleibt der Fehler für dieselbe Session
 * stehen, bis neu gesendet wird. Ausnahmen: Session-Wechsel und Lade-Fehler
 * (`load`), die sich mit dem geglückten Reload erledigt haben.
 */
export function errorAfterReload(
  current: ErrorSlice,
  sessionId: string,
): Pick<ErrorSlice, "error" | "errorKind"> {
  const keep = current.error !== null && current.loadedFor === sessionId && current.errorKind !== "load"
  return keep ? { error: current.error, errorKind: current.errorKind } : { error: null, errorKind: null }
}
