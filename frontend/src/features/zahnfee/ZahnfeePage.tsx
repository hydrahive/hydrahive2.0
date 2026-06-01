import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Loader2, Play, Save, RotateCcw } from "lucide-react"
import { zahnfeeApi, type ZahnfeeConfig, type Briefing } from "./api"
import { ModelPicker } from "@/features/chat/ModelPicker"

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

export function ZahnfeePage() {
  const { t } = useTranslation("zahnfee")
  const [cfg, setCfg] = useState<ZahnfeeConfig | null>(null)
  const [briefing, setBriefing] = useState<Briefing | null>(null)
  const [saving, setSaving] = useState(false)
  const [running, setRunning] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    zahnfeeApi.config().then(setCfg).catch(() => {})
    zahnfeeApi.briefing().then((r) => setBriefing(r.briefing)).catch(() => {})
  }, [])

  async function save() {
    if (!cfg) return
    setSaving(true)
    try {
      const updated = await zahnfeeApi.updateConfig(cfg)
      setCfg(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setSaving(false)
    }
  }

  async function runNow() {
    setRunning(true)
    try {
      const r = await zahnfeeApi.run()
      setBriefing(r.briefing)
    } finally {
      setRunning(false)
    }
  }

  if (!cfg) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 size={20} className="animate-spin text-zinc-500" />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 flex flex-col gap-8">
      <div className="flex items-center gap-3">
        <span className="text-4xl">🦷</span>
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Zahnfee</h1>
          <p className="text-sm text-zinc-500">{t("subtitle")}</p>
        </div>
      </div>

      {/* Aktuelles Briefing */}
      <div className="rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900/90 to-zinc-950/90 p-6">
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
        {briefing ? (
          <BriefingPreview briefing={briefing} />
        ) : (
          <p className="text-sm text-zinc-500 italic">{t("briefing.empty")}</p>
        )}
      </div>

      {/* Config */}
      <div className="rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900/90 to-zinc-950/90 p-6 flex flex-col gap-5">
        <h2 className="text-sm font-semibold text-zinc-300">{t("config.title")}</h2>

        {/* Aktiviert */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={cfg.enabled}
            onChange={(e) => setCfg({ ...cfg, enabled: e.target.checked })}
            className="w-4 h-4 accent-violet-500"
          />
          <span className="text-sm text-zinc-300">{t("config.enabled")}</span>
        </label>

        {/* Modell */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs text-zinc-500 font-medium uppercase tracking-wider">{t("config.model")}</label>
          <ModelPicker
            current={cfg.model}
            hint={t("config.model_hint")}
            showReset
            onPick={(m) => setCfg({ ...cfg, model: m })}
            onReset={() => setCfg({ ...cfg, model: "" })}
          />
        </div>

        {/* Uhrzeit + Lookback */}
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-zinc-500 font-medium uppercase tracking-wider">{t("config.run_hour")}</label>
            <input
              type="number"
              min={0}
              max={23}
              value={cfg.run_hour}
              onChange={(e) => setCfg({ ...cfg, run_hour: Number(e.target.value) })}
              className="bg-zinc-800 border border-white/[8%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-violet-500/50"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs text-zinc-500 font-medium uppercase tracking-wider">{t("config.lookback")}</label>
            <input
              type="number"
              min={1}
              max={720}
              value={cfg.lookback_hours}
              onChange={(e) => setCfg({ ...cfg, lookback_hours: Number(e.target.value) })}
              className="bg-zinc-800 border border-white/[8%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-violet-500/50"
            />
          </div>
        </div>

        {/* Quellen */}
        <div className="flex flex-col gap-2">
          <label className="text-xs text-zinc-500 font-medium uppercase tracking-wider">{t("config.sources")}</label>
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={cfg.source_datamining}
              onChange={(e) => setCfg({ ...cfg, source_datamining: e.target.checked })}
              className="w-4 h-4 accent-violet-500"
            />
            <span className="text-sm text-zinc-300">{t("config.source_datamining")}</span>
          </label>
          <label className="flex items-center gap-3 cursor-pointer opacity-50">
            <input
              type="checkbox"
              checked={cfg.source_mail}
              onChange={(e) => setCfg({ ...cfg, source_mail: e.target.checked })}
              className="w-4 h-4 accent-violet-500"
            />
            <span className="text-sm text-zinc-300">{t("config.source_mail")} <span className="text-zinc-600 text-xs">{t("config.source_mail_unavailable")}</span></span>
          </label>
        </div>

        {/* Soul */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs text-zinc-500 font-medium uppercase tracking-wider">{t("config.soul")}</label>
            <button
              onClick={() => setCfg({ ...cfg, soul: "" })}
              className="flex items-center gap-1 text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
              title={t("config.soul_reset")}
            >
              <RotateCcw size={11} /> {t("config.soul_reset_short")}
            </button>
          </div>
          <textarea
            value={cfg.soul}
            onChange={(e) => setCfg({ ...cfg, soul: e.target.value })}
            rows={12}
            className="bg-zinc-800 border border-white/[8%] rounded-lg px-3 py-2 text-sm text-zinc-200 font-mono resize-y focus:outline-none focus:border-violet-500/50 leading-relaxed"
          />
        </div>

        <button
          onClick={save}
          disabled={saving}
          className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white text-sm font-medium transition-colors"
        >
          {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
          {saved ? t("config.saved") : saving ? t("config.saving") : t("config.save")}
        </button>
      </div>
    </div>
  )
}
