import { type CSSProperties, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"
import { Loader2, Play, Settings as SettingsIcon } from "lucide-react"
import { rgbFor } from "@/shared/colors"
import { HelpButton } from "@/i18n/HelpButton"
import { zahnfeeApi, type Briefing } from "./api"

function Section({ title, content, accent }: { title: string; content: string; accent: string }) {
  if (!content) return null
  return (
    <div className={`rounded-xl border p-4 ${accent}`}>
      <p className="text-xs font-semibold uppercase tracking-wider mb-2 opacity-70">{title}</p>
      <p className="text-sm whitespace-pre-wrap leading-relaxed">{content}</p>
    </div>
  )
}

function BriefingPreview({ briefing }: { briefing: Briefing }) {
  const { t } = useTranslation("zahnfee")
  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs text-zinc-500">
        {t("briefing.generated_at")}: {new Date(briefing.generated_at).toLocaleString()} · {t("briefing.date")}: {briefing.date}
      </p>
      {briefing.error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4">
          <p className="text-xs font-semibold text-rose-400 mb-1">{t("briefing.error")}</p>
          <p className="text-sm text-rose-300 font-mono">{briefing.error}</p>
        </div>
      )}
      <Section title={t("briefing.sections.open")} content={briefing.open_items} accent="border-amber-500/20 bg-amber-500/5 text-amber-200" />
      <Section title={t("briefing.sections.went_well")} content={briefing.went_well} accent="border-emerald-500/20 bg-emerald-500/5 text-emerald-200" />
      <Section title={t("briefing.sections.went_badly")} content={briefing.went_badly} accent="border-rose-500/20 bg-rose-500/5 text-rose-200" />
      <Section title={t("briefing.sections.today")} content={briefing.today} accent="border-violet-500/20 bg-violet-500/5 text-violet-200" />
    </div>
  )
}

/**
 * Zahnfee — AUSWERTUNG (das tägliche Briefing). Die Einstellungen wurden in den
 * zentralen Settings-Hub ausgelagert (Trennung Auswertung/Einstellung).
 */
export function ZahnfeePage() {
  const { t } = useTranslation("zahnfee")
  const [briefing, setBriefing] = useState<Briefing | null>(null)
  const [running, setRunning] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    zahnfeeApi.briefing()
      .then((r) => setBriefing(r.briefing))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  async function runNow() {
    setRunning(true)
    try {
      const r = await zahnfeeApi.run()
      setBriefing(r.briefing)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 flex flex-col gap-8">
      <div className="flex items-center gap-3">
        <span className="text-4xl">🦷</span>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-zinc-100">Zahnfee</h1>
          <p className="text-sm text-zinc-500">{t("subtitle")}</p>
        </div>
        <HelpButton topic="zahnfee" />
        <Link
          to="/settings"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs transition-colors"
          title={t("config.title")}
        >
          <SettingsIcon size={13} /> {t("config.title")}
        </Link>
      </div>

      <div className="box overflow-hidden p-6" style={{ "--c": rgbFor("/profile") } as CSSProperties}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-zinc-300">{t("briefing.title")}</h2>
          <button
            onClick={runNow}
            disabled={running}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white text-xs font-medium transition-colors"
          >
            {running ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
            {running ? t("briefing.running") : t("briefing.run_now")}
          </button>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 size={18} className="animate-spin text-zinc-500" />
          </div>
        ) : briefing ? (
          <BriefingPreview briefing={briefing} />
        ) : (
          <p className="text-sm text-zinc-500 italic">{t("briefing.empty")}</p>
        )}
      </div>
    </div>
  )
}
