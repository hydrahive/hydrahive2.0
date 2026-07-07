// Vite glob-Import: lädt Hilfe-Inhalte beim ersten Zugriff lazy nach.
const modules = import.meta.glob("./*/*.md", { query: "?raw", import: "default" })

// Alle Hilfe-Themen. Ein Topic braucht eine Datei help/<lang>/<topic>.md.
// Fehlt sie, zeigt der Drawer den "fehlt noch"-Hinweis (kein Crash).
export type HelpTopic =
  // Kern-Nav
  | "dashboard" | "buddy" | "chat" | "werkstatt" | "agents" | "projects"
  | "communication" | "teamchat"
  // Automatisierung
  | "butler" | "zahnfee" | "skills" | "mcp" | "plugins"
  // Infrastruktur
  | "vms" | "containers" | "federation" | "streaming" | "datamining" | "memory"
  // Konfiguration
  | "llm" | "credentials" | "system" | "extensions" | "modules" | "users" | "settings"
  // Einstieg
  | "onboarding"
  // Module
  | "atelier" | "patientenakte" | "cryptoboard" | "notizbuch" | "scratchpad"
  | "deepresearch" | "homeassistant" | "archiver" | "blueprint" | "boardgames"
  | "minigames" | "musicplayer" | "tasks" | "videoeditor"

export async function loadHelp(topic: HelpTopic, lang: string): Promise<string> {
  const code = lang.split("-")[0]
  const tryPaths = [
    `./${code}/${topic}.md`,
    `./de/${topic}.md`,
    `./en/${topic}.md`,
  ]
  for (const p of tryPaths) {
    const loader = modules[p] as (() => Promise<string>) | undefined
    if (loader) return await loader()
  }
  return "_Hilfe für dieses Thema fehlt noch._"
}
