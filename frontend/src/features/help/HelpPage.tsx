import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Loader2 } from "lucide-react"
import { Markdown } from "@/features/chat/Markdown"
import { type HelpTopic, loadHelp } from "@/i18n/help/loader"

const TOPICS: { id: HelpTopic; labelDe: string; labelEn: string }[] = [
  { id: "dashboard", labelDe: "Dashboard", labelEn: "Dashboard" },
  { id: "chat",      labelDe: "Chat",      labelEn: "Chat" },
  { id: "agents",    labelDe: "Agenten",   labelEn: "Agents" },
  { id: "projects",  labelDe: "Projekte",  labelEn: "Projects" },
  { id: "llm",       labelDe: "LLM",       labelEn: "LLM" },
  { id: "mcp",       labelDe: "MCP",       labelEn: "MCP" },
  { id: "system",    labelDe: "System",    labelEn: "System" },
]

export function HelpPage() {
  const { i18n } = useTranslation()
  const [topic, setTopic] = useState<HelpTopic>("dashboard")
  const [content, setContent] = useState("")
  const [loading, setLoading] = useState(false)
  const lang = i18n.language.split("-")[0]

  useEffect(() => {
    setLoading(true)
    loadHelp(topic, i18n.language)
      .then(setContent)
      .finally(() => setLoading(false))
  }, [topic, i18n.language])

  return (
    <div className="grid grid-cols-1 md:grid-cols-[200px_1fr] gap-4 max-w-5xl">
      <aside className="md:sticky md:top-2 md:self-start">
        <h2 className="text-sm font-bold text-white mb-3 px-2">
          {lang === "de" ? "Handbuch" : "Manual"}
        </h2>
        <nav className="space-y-0.5">
          {TOPICS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTopic(t.id)}
              className={`w-full text-left px-3 py-1.5 rounded-md text-sm transition-colors ${
                topic === t.id
                  ? "bg-violet-500/15 text-violet-200 border border-violet-500/30"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[5%] border border-transparent"
              }`}
            >
              {lang === "de" ? t.labelDe : t.labelEn}
            </button>
          ))}
        </nav>
      </aside>

      <article className="rounded-xl border border-white/[6%] bg-white/[2%] p-5 min-h-[300px]">
        {loading ? (
          <div className="flex items-center gap-2 text-zinc-400 text-sm">
            <Loader2 size={14} className="animate-spin" />
            <span>{lang === "de" ? "Lade…" : "Loading…"}</span>
          </div>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none">
            <Markdown text={content} />
          </div>
        )}
      </article>
    </div>
  )
}
