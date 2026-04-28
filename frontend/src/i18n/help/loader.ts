// Vite glob-Import: lädt Hilfe-Inhalte beim ersten Zugriff lazy nach.
const modules = import.meta.glob("./*/*.md", { query: "?raw", import: "default" })

export type HelpTopic =
  | "dashboard" | "chat" | "agents" | "projects"
  | "llm" | "mcp" | "system"

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
