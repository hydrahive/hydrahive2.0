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

export const mediaOfflineActions = [
  { id: "atelier", label: "Atelier öffnen", kind: "local-link", path: "/atelier", description: "Vorhandene Produktionszentrale öffnen." },
  { id: "streaming", label: "Streaming", kind: "local-link", path: "/streaming", description: "Medien-Downloads und Streaming-Helfer öffnen." },
  { id: "musicplayer", label: "Musikplayer", kind: "local-link", path: "/musicplayer", description: "Lokale und generierte Tracks verwalten." },
  { id: "videoeditor", label: "Videoeditor", kind: "local-link", path: "/videoeditor", description: "Schnitt-/Timeline-Modul öffnen." },
] satisfies CockpitAction[]

export const vaultOfflineActions = [
  { id: "akte", label: "Patientenakte", kind: "local-link", path: "/akte", description: "Medizinische Akte öffnen." },
  { id: "cryptoboard", label: "Crypto Board", kind: "local-link", path: "/cryptoboard", description: "Crypto-Modul öffnen." },
  { id: "scratchpad", label: "Scratchpad", kind: "local-link", path: "/scratchpad", description: "Private Notizen öffnen." },
  { id: "credentials", label: "Credentials", kind: "local-link", path: "/credentials", description: "Secrets-Verwaltung mit bestehenden Guards öffnen." },
  { id: "documents", label: "Dokumente/OCR", kind: "status-only", description: "Geplant, bis Upload-/OCR-Backend vollständig portiert ist." },
] satisfies CockpitAction[]

export const adminOfflineActions = [
  { id: "system", label: "System", kind: "local-link", path: "/system", description: "Lokale Systemverwaltung öffnen." },
  { id: "users", label: "User", kind: "local-link", path: "/users", description: "Accounts und Rollen öffnen." },
  { id: "modules", label: "Module", kind: "local-link", path: "/modules", description: "Modulverwaltung öffnen." },
  { id: "extensions", label: "Extensions", kind: "local-link", path: "/extensions", description: "Erweiterungen öffnen." },
  { id: "plugins", label: "Plugins", kind: "local-link", path: "/plugins", description: "Pluginverwaltung öffnen." },
  { id: "credentials", label: "Credentials", kind: "local-link", path: "/credentials", description: "Secrets-Verwaltung öffnen." },
] satisfies CockpitAction[]

export const explicitAiActions = [
  { id: "buddy-chat", label: "Buddy-Chat", kind: "explicit-ai", path: "/buddy", description: "Nur das Chatfeld sendet LLM-Anfragen." },
  { id: "media-agent", label: "Media-Agent", kind: "explicit-ai", path: "/buddy", description: "Optional: Medienfragen bewusst im Buddy stellen." },
  { id: "vault-agent", label: "Vault-Agent", kind: "explicit-ai", path: "/buddy", description: "Optional: sensible Auswertung nur bewusst starten." },
  { id: "admin-agent", label: "Admin-Agent", kind: "explicit-ai", path: "/buddy", description: "Optional: Admin-Analyse bewusst im Buddy starten." },
] satisfies CockpitAction[]
