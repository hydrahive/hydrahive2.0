import type { ActivityEntry } from "./api"

export interface PixelProps {
  agentTools: Record<string, string[]>
  activeAgents: string[]
  doneAgents: string[]
}

/**
 * Leitet die Monitor-Props aus dem Live-Feed ab.
 * - scope "all": alle laufenden Agenten.
 * - scope "chat": aktiver Agent + laufende Agenten passend zu ask_agent-Zielen.
 */
export function selectPixelAgents(
  running: ActivityEntry[],
  scope: "chat" | "all",
  activeAgentName: string | null,
  askTargets: string[],
  doneNames: string[],
): PixelProps {
  const targets = new Set(askTargets)
  const visible = scope === "all"
    ? running
    : running.filter((a) => a.name === activeAgentName || targets.has(a.name) || targets.has(a.agent_id))
  const doneVisible = scope === "all"
    ? doneNames
    : doneNames.filter((n) => n === activeAgentName || targets.has(n))

  const agentTools: Record<string, string[]> = {}
  for (const a of visible) agentTools[a.name] = a.current_tool ? [a.current_tool] : []
  for (const n of doneVisible) if (!agentTools[n]) agentTools[n] = []

  return {
    agentTools,
    activeAgents: visible.map((a) => a.name),
    doneAgents: doneVisible,
  }
}
