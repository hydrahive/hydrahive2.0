// Vite glob-Import: lädt Hilfe-Inhalte beim ersten Zugriff lazy nach.
// Zwei Quellen: Kern-Artikel hier (help/<lang>/<topic>.md) und Artikel, die Module mitbringen
// (<modul>/frontend/help/<lang>/<topic>.md → nach der Installation src/modules/<id>/help/…).
// Gibt es ein Thema in beiden, gewinnt das Modul: Seine Hilfe wird mit dem Modul gepflegt und ist aktueller.
const core = import.meta.glob("./*/*.md", { query: "?raw", import: "default" })
const fromModules = import.meta.glob("../../modules/*/help/*/*.md", { query: "?raw", import: "default" })

/** Kern-Themen (Tippfehler-Schutz für Kern-Seiten). Module bringen eigene Themen mit, daher offen für weitere. */
export type CoreHelpTopic =
  // Kern-Nav
  | "dashboard" | "buddy" | "chat" | "werkstatt" | "agents" | "projects"
  | "communication" | "teamchat"
  // Automatisierung
  | "butler" | "zahnfee" | "skills" | "mcp" | "plugins"
  // Infrastruktur
  | "vms" | "containers" | "nodes" | "jobs" | "federation" | "streaming" | "datamining" | "memory"
  // Konfiguration
  | "llm" | "credentials" | "system" | "extensions" | "modules" | "users" | "settings" | "access"
  // Wartung
  | "archive"
  // Einstieg
  | "onboarding" | "helpdesk"
  // Modul-Themen stehen nicht hier: Jedes Modul bringt seine Hilfe selbst mit (<modul>/frontend/help/<lang>/<id>.md).

export type HelpTopic = CoreHelpTopic | (string & {})

type Loader = () => Promise<string>
const MISSING = "_Hilfe für dieses Thema fehlt noch._"

/** Pfad → { topic, lang, source }. Nur Dateinamen aus dem Build, nie Eingaben von außen. */
function parse(path: string): { topic: string; lang: string; source: "core" | "module"; module?: string } | null {
  const m = path.match(/^\.\.\/\.\.\/modules\/([^/]+)\/help\/([a-z]{2})\/([a-z0-9][a-z0-9_-]*)\.md$/)
  if (m) return { module: m[1], lang: m[2], topic: m[3], source: "module" }
  const c = path.match(/^\.\/([a-z]{2})\/([a-z0-9][a-z0-9_-]*)\.md$/)
  return c ? { lang: c[1], topic: c[2], source: "core" } : null
}

/** Index: topic → lang → Loader (Modul vor Kern). */
export function buildIndex(coreFiles: Record<string, unknown>, moduleFiles: Record<string, unknown>) {
  const index = new Map<string, Map<string, Loader>>()
  const origin = new Map<string, { source: "core" | "module"; module?: string }>()
  for (const [files, isModule] of [[coreFiles, false], [moduleFiles, true]] as const) {
    for (const [path, loader] of Object.entries(files)) {
      const p = parse(path)
      if (!p || (p.source === "module") !== isModule) continue
      const langs = index.get(p.topic) ?? new Map<string, Loader>()
      langs.set(p.lang, loader as Loader)          // Module laufen als zweites → überschreiben den Kern
      index.set(p.topic, langs)
      if (isModule || !origin.has(p.topic)) origin.set(p.topic, { source: p.source, module: p.module })
    }
  }
  return { index, origin }
}

const { index, origin } = buildIndex(core, fromModules)

export async function loadHelp(topic: HelpTopic, lang: string): Promise<string> {
  const langs = index.get(topic)
  if (!langs) return MISSING
  for (const code of [lang.split("-")[0], "de", "en"]) {
    const loader = langs.get(code)
    if (loader) return await loader()
  }
  return MISSING
}

export interface HelpEntry { topic: string; title: string; source: "core" | "module"; module?: string }

/** Alle vorhandenen Artikel mit Titel (erste „# Überschrift“), für die Hilfe-Seite. */
export async function listHelp(lang: string): Promise<HelpEntry[]> {
  const entries = await Promise.all([...index.keys()].map(async (topic) => {
    const text = await loadHelp(topic, lang)
    const title = text.match(/^#\s+(.+?)\s*$/m)?.[1] ?? topic
    return { topic, title, ...origin.get(topic)! }
  }))
  return entries.sort((a, b) => a.title.localeCompare(b.title, lang))
}
