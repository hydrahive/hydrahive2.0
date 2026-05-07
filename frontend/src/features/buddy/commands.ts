/**
 * Slash-Commands für die Buddy-Page. Deterministisch, kein LLM-Roundtrip.
 * Eingabe `/foo bar` wird hier abgefangen und über REST-Endpoints
 * verarbeitet, Ergebnis als persistente Bubble (oder localMsg) angezeigt.
 */
import { agentsApi } from "@/features/agents/api"
import { chatApi } from "@/features/chat/api"
import type { Message } from "@/features/chat/types"
import { buddyApi, type BuddyState } from "./api"

export interface CommandResult {
  message: string
  newSessionId?: string
}

const HELP_TEXT = [
  "Verfügbare Befehle:",
  "  /help               — diese Liste",
  "  /clear              — frischer Chat (alte Session bleibt im Verlauf)",
  "  /reset              — alias für /clear",
  "  /remember [name]    — speichert den aktuellen Verlauf als Memory",
  "  /model [name]       — Buddy-Modell anzeigen oder wechseln",
  "  /character          — neuen Charakter würfeln",
  "  /compact            — manuelle Compaction der Buddy-Session",
  "  /tokens             — Token-Stand + Window-Auslastung",
  "  /title <text>       — Buddy-Session umbenennen",
  "  /system             — System-Prompt anzeigen",
  "  /tools              — verfügbare Tools im Backend",
  "  /agent              — Buddy-Agent-Info",
  "  /soul               — Soul-Komponenten anzeigen",
  "  /export             — Verlauf als Markdown ausgeben",
].join("\n")

export function isCommand(text: string): boolean {
  return text.trimStart().startsWith("/")
}

async function modelCmd(arg: string): Promise<CommandResult> {
  if (!arg.trim()) {
    const r = await buddyApi.models()
    return { message: [`Aktuell: ${r.current}`, "Verfügbar:", ...r.available.map((m) => `  - ${m}`), "", "Wechseln mit `/model <name>`"].join("\n") }
  }
  const r = await buddyApi.setModel(arg.trim())
  return { message: r.message }
}

async function compactCmd(state: BuddyState): Promise<CommandResult> {
  const r = await chatApi.compact(state.session_id)
  if (r.skipped) return { message: `Compaction übersprungen (${r.reason_code ?? "unklar"}).` }
  return { message: `Compaction OK: ${r.summarized_count ?? 0} → 1 Summary, ${r.kept_count ?? 0} Messages behalten.` }
}

async function tokensCmd(state: BuddyState): Promise<CommandResult> {
  const r = await chatApi.tokens(state.session_id)
  const pct = r.context_window ? Math.round((r.used / r.context_window) * 100) : 0
  return { message: [
    `Tokens: ${r.used.toLocaleString()} / ${r.context_window.toLocaleString()} (${pct}%)`,
    `Compact-Threshold: ${r.compact_threshold.toLocaleString()}`,
    `Modell: ${r.model ?? "—"}`,
  ].join("\n") }
}

async function titleCmd(arg: string, state: BuddyState): Promise<CommandResult> {
  const newTitle = arg.trim()
  if (!newTitle) return { message: "Nutzung: /title <neuer Titel>" }
  await chatApi.updateSession(state.session_id, { title: newTitle })
  return { message: `Titel: ${newTitle}` }
}

async function systemCmd(state: BuddyState): Promise<CommandResult> {
  const r = await agentsApi.getSystemPrompt(state.agent_id)
  return { message: r.prompt ? `System-Prompt:\n\n${r.prompt}` : "System-Prompt ist leer." }
}

async function toolsCmd(): Promise<CommandResult> {
  const tools = await agentsApi.listTools()
  return { message: ["Verfügbare Tools im Backend:", ...tools.map((t) => `  - ${t.name}`)].join("\n") }
}

async function agentCmd(state: BuddyState): Promise<CommandResult> {
  return { message: [`Agent: ${state.agent_name}  (id ${state.agent_id.slice(0, 8)}…)`, `Modell: ${state.model}`, `Session: ${state.session_id.slice(0, 8)}…`].join("\n") }
}

async function soulCmd(state: BuddyState): Promise<CommandResult> {
  try {
    const r = await agentsApi.getSoul(state.agent_id)
    const lines: string[] = ["Soul-Komponenten:"]
    for (const [k, v] of Object.entries(r.components)) {
      lines.push(`\n## ${k}\n${v}`)
    }
    return { message: lines.join("\n") }
  } catch (e) {
    return { message: `Soul nicht abrufbar (${e instanceof Error ? e.message : "Fehler"})` }
  }
}

async function exportCmd(state: BuddyState): Promise<CommandResult> {
  const msgs: Message[] = await chatApi.listMessages(state.session_id)
  const lines: string[] = ["# Buddy-Chat-Export", ""]
  for (const m of msgs) {
    if (m.role === "compaction") continue
    const role = m.role === "user" ? "User" : m.role === "assistant" ? "Assistant" : m.role
    lines.push(`## ${role} — ${m.created_at}`)
    if (typeof m.content === "string") lines.push(m.content)
    else if (!Array.isArray(m.content)) { /* null — skip */ }
    else for (const b of m.content) {
      if (b.type === "text") lines.push(b.text)
      else if (b.type === "tool_use") lines.push(`\`tool_use: ${b.name}\` ${JSON.stringify(b.input)}`)
      else if (b.type === "tool_result") lines.push(`\`tool_result\` ${typeof b.content === "string" ? b.content : JSON.stringify(b.content)}`)
    }
    lines.push("")
  }
  return { message: lines.join("\n") }
}

export async function runCommand(text: string, state: BuddyState): Promise<CommandResult> {
  const trimmed = text.trim()
  const space = trimmed.indexOf(" ")
  const cmd = (space === -1 ? trimmed : trimmed.slice(0, space)).toLowerCase()
  const arg = space === -1 ? "" : trimmed.slice(space + 1)
  try {
    switch (cmd) {
      case "/help": return { message: HELP_TEXT }
      case "/clear": case "/reset": {
        const r = await buddyApi.clear()
        return { message: r.message, newSessionId: r.session_id }
      }
      case "/remember": {
        const r = await buddyApi.remember(arg.trim() ? { name: arg.trim() } : {})
        return { message: r.message }
      }
      case "/model": case "/models": return await modelCmd(arg)
      case "/character": {
        const r = await buddyApi.character()
        return { message: r.message, newSessionId: r.session_id }
      }
      case "/compact": return await compactCmd(state)
      case "/tokens": return await tokensCmd(state)
      case "/title": case "/rename": return await titleCmd(arg, state)
      case "/system": case "/sys": return await systemCmd(state)
      case "/tools": return await toolsCmd()
      case "/agent": return await agentCmd(state)
      case "/soul": return await soulCmd(state)
      case "/export": return await exportCmd(state)
      default: return { message: `Unbekannter Befehl ${cmd}. Tippe /help.` }
    }
  } catch (e) {
    return { message: `Fehler: ${e instanceof Error ? e.message : String(e)}` }
  }
}
