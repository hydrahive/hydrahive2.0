import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Markdown } from "@/features/chat/Markdown"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { type HelpTopic, loadHelp } from "@/i18n/help/loader"

const TOPICS: { id: HelpTopic; labelDe: string; labelEn: string }[] = [
  { id: "dashboard", labelDe: "Dashboard", labelEn: "Dashboard" },
  { id: "chat", labelDe: "Chat", labelEn: "Chat" },
  { id: "agents", labelDe: "Agenten", labelEn: "Agents" },
  { id: "projects", labelDe: "Projekte", labelEn: "Projects" },
  { id: "llm", labelDe: "LLM", labelEn: "LLM" },
  { id: "mcp", labelDe: "MCP", labelEn: "MCP" },
  { id: "system", labelDe: "System", labelEn: "System" },
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
    <CockpitShell
      title={lang === "de" ? "Hilfe" : "Help"}
      className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]"
      hideHeader
    >
      <CockpitTopbar active="/help" context={lang === "de" ? "Handbuch und Seitendokumentation" : "Manual and page documentation"} />
      <main className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">
        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-4 lg:grid-cols-[220px_minmax(0,1fr)]">
          <aside className="self-start rounded-[4px] border border-[#2a364b] bg-[#151c2b] p-3 lg:sticky lg:top-0">
            <p className="px-2 pb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-[#69d7ff]">
              {lang === "de" ? "Handbuch" : "Manual"}
            </p>
            <nav className="space-y-1" aria-label={lang === "de" ? "Hilfe-Themen" : "Help topics"}>
              {TOPICS.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setTopic(item.id)}
                  className={`w-full rounded-[4px] border px-3 py-2 text-left text-sm transition-colors ${
                    topic === item.id
                      ? "border-[#69d7ff]/45 bg-[#1c2940] font-semibold text-[#69d7ff]"
                      : "border-transparent text-[#8d9ab0] hover:border-[#2a364b] hover:bg-[#111827] hover:text-[#e8eef8]"
                  }`}
                >
                  {lang === "de" ? item.labelDe : item.labelEn}
                </button>
              ))}
            </nav>
          </aside>

          <article className="min-h-[420px] rounded-[4px] border border-[#2a364b] bg-[#151c2b] p-5 text-[#c8d2df]">
            {loading ? (
              <div className="flex items-center gap-2 text-sm text-[#8d9ab0]">
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
      </main>
    </CockpitShell>
  )
}
