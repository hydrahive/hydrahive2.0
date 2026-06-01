import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Markdown } from "@/features/chat/Markdown"
import { scratchpadApi } from "./api"

export function ScratchpadPage() {
  const { t } = useTranslation("scratchpad")
  const [userText, setUserText] = useState("")
  const [agentText, setAgentText] = useState("")
  const [loading, setLoading] = useState(true)
  const [saved, setSaved] = useState(true)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    scratchpadApi.get()
      .then((d) => { setUserText(d.user_content); setAgentText(d.agent_content) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const onChange = (v: string) => {
    setUserText(v)
    setSaved(false)
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      scratchpadApi.saveUser(v).then(() => setSaved(true)).catch(() => {})
    }, 800)
  }

  const clearAgent = () => {
    if (!confirm(t("clear_confirm"))) return
    scratchpadApi.clearAgent().then(() => setAgentText("")).catch(() => {})
  }

  if (loading) {
    return <div className="h-48 m-6 rounded-xl bg-zinc-900/50 animate-pulse" />
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold text-zinc-100">{t("title")}</h1>
        <span className="text-xs text-zinc-600">{saved ? t("saved") : t("saving")}</span>
      </div>

      <section className="space-y-2">
        <h2 className="text-sm font-medium text-zinc-300">{t("my_ideas")}</h2>
        <div className="grid grid-cols-2 gap-4">
          <textarea
            value={userText}
            onChange={(e) => onChange(e.target.value)}
            placeholder={t("placeholder")}
            className="min-h-[24rem] rounded-xl border border-white/[8%] bg-zinc-900 px-4 py-3 text-sm text-zinc-100 placeholder-zinc-600 font-mono resize-y"
          />
          <div className="min-h-[24rem] rounded-xl border border-white/[6%] bg-zinc-900/40 px-4 py-3 overflow-auto">
            <Markdown text={userText || t("empty_preview")} />
          </div>
        </div>
      </section>

      <section className="space-y-2">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-medium text-zinc-300">{t("agent_notes")}</h2>
          <span className="text-xs text-zinc-600">{t("agent_notes_hint")}</span>
          <button
            onClick={clearAgent}
            className="ml-auto text-xs text-zinc-500 hover:text-red-400 px-2 py-1 rounded-lg border border-white/[6%] hover:bg-white/[4%] transition-colors"
          >
            {t("clear")}
          </button>
        </div>
        <div className="rounded-xl border border-violet-500/15 bg-violet-500/[4%] px-4 py-3">
          <Markdown text={agentText || t("agent_notes_empty")} />
        </div>
      </section>
    </div>
  )
}
