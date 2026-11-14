import type { ActivityEntry } from "@/features/chat/api"

export interface StandupStats {
  total: number
  delegated: number
  errored: number
}

/** Aggregat-Übersicht oberhalb des Büros (Spec agent-office.md §8.1, Claw3D-Idee „Standup"). */
export function standupStats(running: ActivityEntry[]): StandupStats {
  return {
    total: running.length,
    delegated: running.filter((a) => Boolean(a.parent_session_id)).length,
    errored: running.filter((a) => (a.last_tool_result_summary ?? "").startsWith("Fehler:")).length,
  }
}
