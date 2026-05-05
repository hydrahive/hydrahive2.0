/**
 * Slash-Commands für ChatPage. Deterministisch, kein LLM-Roundtrip.
 * Eingabe `/foo bar` wird hier abgefangen, Ergebnis als persistente
 * Bubble in die Session gespeichert (siehe BuddyPage-Pattern).
 */
import { llmApi } from "@/features/llm/api"
import { agentsApi } from "@/features/agents/api"
import { chatApi } from "./api"
import type { AgentBrief, Session } from "./types"

export interface ChatCommandResult {
  message: string
  newSessionId?: string
  agentChanged?: AgentBrief
}

const HELP_TEXT = [
  "Verfügbare Befehle in dieser Session:",
  "  /help — diese Liste",
  "  /clear — neue Session im selben Projekt + Agent (alte bleibt im Verlauf)",
  "  /model — verfügbare Modelle anzeigen",
  "  /model <name> — Agent-Modell wechseln",
].join("\n")

export function isCommand(text: string): boolean {
  return text.trimStart().startsWith("/")
}

async function modelCmd(arg: string, agent: AgentBrief): Promise<ChatCommandResult> {
  if (!arg.trim()) {
    const cfg = await llmApi.getConfig()
    const models = Array.from(new Set(cfg.providers.flatMap((p) => p.models)))
    const lines = [
      `Aktuell: ${agent.llm_model}`,
      "Verfügbar:",
      ...models.map((m) => `  - ${m}`),
      "",
      "Wechseln mit `/model <name>`",
    ]
    return { message: lines.join("\n") }
  }
  const target = arg.trim()
  const cfg = await llmApi.getConfig()
  const all = new Set(cfg.providers.flatMap((p) => p.models))
  if (!all.has(target)) {
    return { message: `Unbekanntes Modell '${target}'. Tippe /model für die Liste.` }
  }
  const updated = await agentsApi.update(agent.id, { llm_model: target })
  return {
    message: `Modell auf ${target} gewechselt.`,
    agentChanged: { ...agent, llm_model: updated.llm_model },
  }
}

async function clearCmd(session: Session, agent: AgentBrief): Promise<ChatCommandResult> {
  const fresh = await chatApi.createSession(agent.id, undefined, session.project_id ?? undefined)
  return {
    message: `Neue Session gestartet: ${fresh.title || fresh.id.slice(0, 8)}`,
    newSessionId: fresh.id,
  }
}

export async function runChatCommand(
  text: string,
  session: Session,
  agent: AgentBrief,
): Promise<ChatCommandResult> {
  const trimmed = text.trim()
  const space = trimmed.indexOf(" ")
  const cmd = (space === -1 ? trimmed : trimmed.slice(0, space)).toLowerCase()
  const arg = space === -1 ? "" : trimmed.slice(space + 1)
  try {
    switch (cmd) {
      case "/help":
        return { message: HELP_TEXT }
      case "/clear":
      case "/reset":
        return await clearCmd(session, agent)
      case "/model":
      case "/models":
        return await modelCmd(arg, agent)
      default:
        return { message: `Unbekannter Befehl ${cmd}. Tippe /help.` }
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    return { message: `Fehler: ${msg}` }
  }
}
