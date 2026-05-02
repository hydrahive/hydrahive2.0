/**
 * Slash-Commands für die Buddy-Page. Deterministisch, kein LLM-Roundtrip.
 * Eingabe `/foo bar` wird hier abgefangen und über REST-Endpoints
 * verarbeitet, Ergebnis als lokale System-Bubble angezeigt.
 */
import { buddyApi } from "./api"

export interface CommandResult {
  message: string
  newSessionId?: string
}

const HELP_TEXT = [
  "Verfügbare Befehle:",
  "  /help — diese Liste",
  "  /clear — frischer Chat (alte Session bleibt im Verlauf)",
  "  /reset — alias für /clear",
  "  /remember — speichert den aktuellen Verlauf als 'session_<datum>'",
  "  /remember <name> — speichert Verlauf unter eigenem Namen",
  "  /model — verfügbare Modelle anzeigen",
  "  /model <name> — Buddy-Modell wechseln",
  "  /character — neuen Charakter würfeln",
].join("\n")

export function isCommand(text: string): boolean {
  return text.trimStart().startsWith("/")
}

async function modelCmd(arg: string): Promise<CommandResult> {
  if (!arg.trim()) {
    const r = await buddyApi.models()
    const lines = [
      `Aktuell: ${r.current}`,
      "Verfügbar:",
      ...r.available.map((m) => `  - ${m}`),
      "",
      "Wechseln mit `/model <name>`",
    ]
    return { message: lines.join("\n") }
  }
  const r = await buddyApi.setModel(arg.trim())
  return { message: r.message }
}

export async function runCommand(text: string): Promise<CommandResult> {
  const trimmed = text.trim()
  const space = trimmed.indexOf(" ")
  const cmd = (space === -1 ? trimmed : trimmed.slice(0, space)).toLowerCase()
  const arg = space === -1 ? "" : trimmed.slice(space + 1)
  try {
    switch (cmd) {
      case "/help":
        return { message: HELP_TEXT }
      case "/clear":
      case "/reset": {
        const r = await buddyApi.clear()
        return { message: r.message, newSessionId: r.session_id }
      }
      case "/remember": {
        // Ohne Args: Verlauf-Snapshot. Mit Args: als Name für den Snapshot.
        const r = await buddyApi.remember(arg.trim() ? { name: arg.trim() } : {})
        return { message: r.message }
      }
      case "/model":
        return await modelCmd(arg)
      case "/character": {
        const r = await buddyApi.character()
        return { message: r.message, newSessionId: r.session_id }
      }
      default:
        return { message: `Unbekannter Befehl ${cmd}. Tippe /help.` }
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    return { message: `Fehler: ${msg}` }
  }
}
