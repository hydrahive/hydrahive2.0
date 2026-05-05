/**
 * Slash-Commands für ChatPage. Deterministisch, kein LLM-Roundtrip.
 * Eingabe `/foo bar` wird hier abgefangen, Ergebnis als persistente
 * Bubble in die Session gespeichert (siehe BuddyPage-Pattern).
 */
import { llmApi } from "@/features/llm/api"
import { agentsApi } from "@/features/agents/api"
import { chatApi } from "./api"
import type { AgentBrief, Message, Session } from "./types"

export interface ChatCommandResult {
  message: string
  newSessionId?: string
  agentChanged?: AgentBrief
  sessionChanged?: Session
}

const HELP_TEXT = [
  "Verfügbare Befehle in dieser Session:",
  "  /help               — diese Liste",
  "  /clear              — neue Session im selben Projekt + Agent",
  "  /model [name]       — Modell anzeigen oder Agent-Modell wechseln",
  "  /compact            — manuelle Compaction der Session-History",
  "  /tokens             — Token-Stand + Window-Auslastung",
  "  /title <text>       — Session umbenennen",
  "  /system             — System-Prompt anzeigen",
  "  /tools              — verfügbare Tools im Backend",
  "  /agent              — Agent dieser Session anzeigen",
  "  /export             — Verlauf als Markdown ausgeben",
].join("\n")

export function isCommand(text: string): boolean {
  return text.trimStart().startsWith("/")
}

async function modelCmd(arg: string, agent: AgentBrief): Promise<ChatCommandResult> {
  if (!arg.trim()) {
    const cfg = await llmApi.getConfig()
    const models = Array.from(new Set(cfg.providers.flatMap((p) => p.models)))
    return { message: [`Aktuell: ${agent.llm_model}`, "Verfügbar:", ...models.map((m) => `  - ${m}`), "", "Wechseln mit `/model <name>`"].join("\n") }
  }
  const target = arg.trim()
  const cfg = await llmApi.getConfig()
  if (!new Set(cfg.providers.flatMap((p) => p.models)).has(target)) {
    return { message: `Unbekanntes Modell '${target}'. Tippe /model für die Liste.` }
  }
  const updated = await agentsApi.update(agent.id, { llm_model: target })
  return { message: `Modell auf ${target} gewechselt.`, agentChanged: { ...agent, llm_model: updated.llm_model } }
}

async function clearCmd(session: Session, agent: AgentBrief): Promise<ChatCommandResult> {
  const fresh = await chatApi.createSession(agent.id, undefined, session.project_id ?? undefined)
  return { message: `Neue Session gestartet: ${fresh.title || fresh.id.slice(0, 8)}`, newSessionId: fresh.id }
}

async function compactCmd(session: Session): Promise<ChatCommandResult> {
  const r = await chatApi.compact(session.id)
  if (r.skipped) return { message: `Compaction übersprungen (${r.reason_code ?? "unklar"}).` }
  return { message: `Compaction OK: ${r.summarized_count ?? 0} → 1 Summary, ${r.kept_count ?? 0} Messages behalten.` }
}

async function tokensCmd(session: Session): Promise<ChatCommandResult> {
  const r = await chatApi.tokens(session.id)
  const pct = r.context_window ? Math.round((r.used / r.context_window) * 100) : 0
  return { message: [
    `Tokens: ${r.used.toLocaleString()} / ${r.context_window.toLocaleString()} (${pct}%)`,
    `Compact-Threshold: ${r.compact_threshold.toLocaleString()}`,
    `Modell: ${r.model ?? "—"}`,
  ].join("\n") }
}

async function titleCmd(arg: string, session: Session): Promise<ChatCommandResult> {
  const newTitle = arg.trim()
  if (!newTitle) return { message: `Aktueller Titel: ${session.title || "(leer)"}\n\nNutzung: /title <neuer Titel>` }
  const updated = await chatApi.updateSession(session.id, { title: newTitle })
  return { message: `Titel: ${updated.title}`, sessionChanged: updated }
}

async function systemCmd(agent: AgentBrief): Promise<ChatCommandResult> {
  const r = await agentsApi.getSystemPrompt(agent.id)
  return { message: r.prompt ? `System-Prompt:\n\n${r.prompt}` : "System-Prompt ist leer." }
}

async function toolsCmd(): Promise<ChatCommandResult> {
  const tools = await agentsApi.listTools()
  const names = tools.map((t) => `  - ${t.name}`)
  return { message: ["Verfügbare Tools im Backend:", ...names].join("\n") }
}

async function agentCmd(agent: AgentBrief, session: Session): Promise<ChatCommandResult> {
  return { message: [
    `Agent: ${agent.name}  (id ${agent.id.slice(0, 8)}…)`,
    `Modell: ${agent.llm_model}`,
    `Session: ${session.title || session.id.slice(0, 8)}`,
  ].join("\n") }
}

function exportCmd(messages: Message[]): ChatCommandResult {
  const lines: string[] = ["# Chat-Export", ""]
  for (const m of messages) {
    if (m.role === "compaction") continue
    const role = m.role === "user" ? "User" : m.role === "assistant" ? "Assistant" : m.role
    lines.push(`## ${role} — ${m.created_at}`)
    if (typeof m.content === "string") lines.push(m.content)
    else for (const b of m.content) {
      if (b.type === "text") lines.push(b.text)
      else if (b.type === "tool_use") lines.push(`\`tool_use: ${b.name}\` ${JSON.stringify(b.input)}`)
      else if (b.type === "tool_result") lines.push(`\`tool_result\` ${typeof b.content === "string" ? b.content : JSON.stringify(b.content)}`)
    }
    lines.push("")
  }
  return { message: lines.join("\n") }
}

export async function runChatCommand(
  text: string,
  session: Session,
  agent: AgentBrief,
  messages: Message[],
): Promise<ChatCommandResult> {
  const trimmed = text.trim()
  const space = trimmed.indexOf(" ")
  const cmd = (space === -1 ? trimmed : trimmed.slice(0, space)).toLowerCase()
  const arg = space === -1 ? "" : trimmed.slice(space + 1)
  try {
    switch (cmd) {
      case "/help": return { message: HELP_TEXT }
      case "/clear": case "/reset": return await clearCmd(session, agent)
      case "/model": case "/models": return await modelCmd(arg, agent)
      case "/compact": return await compactCmd(session)
      case "/tokens": return await tokensCmd(session)
      case "/title": case "/rename": return await titleCmd(arg, session)
      case "/system": case "/sys": return await systemCmd(agent)
      case "/tools": return await toolsCmd()
      case "/agent": return await agentCmd(agent, session)
      case "/export": return exportCmd(messages)
      default: return { message: `Unbekannter Befehl ${cmd}. Tippe /help.` }
    }
  } catch (e) {
    return { message: `Fehler: ${e instanceof Error ? e.message : String(e)}` }
  }
}
