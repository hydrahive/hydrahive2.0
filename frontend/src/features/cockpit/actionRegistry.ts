export type CockpitActionKind = "local-link" | "local-action" | "status-only" | "explicit-ai"

export interface CockpitAction {
  id: string
  label: string
  kind: CockpitActionKind
  description?: string
  path?: string
}

export function openLocalPath(path: string) {
  window.open(path, "_self")
}

export const buddyOfflineActions = [
  { id: "today", label: "Was liegt an?", kind: "local-action", description: "Zeigt eine lokale Übersicht ohne LLM." },
  { id: "remember", label: "Idee merken", kind: "local-link", path: "/scratchpad", description: "Öffnet Scratchpad statt Chat-Prompt." },
  { id: "project", label: "Projekt öffnen", kind: "local-link", path: "/projects", description: "Öffnet das Projekt-Cockpit." },
] satisfies CockpitAction[]

export const explicitAiActions = [
  { id: "buddy-chat", label: "Buddy-Chat", kind: "explicit-ai", description: "Nur das Chatfeld sendet LLM-Anfragen." },
] satisfies CockpitAction[]
