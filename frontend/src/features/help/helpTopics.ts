import type { HelpEntry } from "@/i18n/help/loader"

/** Erste Themen oben, der Rest alphabetisch (Kern und Module gemischt). */
const FIRST = ["onboarding", "buddy", "chat", "agents", "projects", "dashboard"]

export function orderTopics(entries: HelpEntry[]): HelpEntry[] {
  const first = FIRST.map((id) => entries.find((e) => e.topic === id)).filter((e): e is HelpEntry => !!e)
  return [...first, ...entries.filter((e) => !FIRST.includes(e.topic))]
}
