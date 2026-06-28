import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Loader2, Save, RotateCcw } from "lucide-react"
import { zahnfeeApi, type ZahnfeeConfig as Cfg } from "./api"
import { ModelPicker } from "@/features/chat/ModelPicker"

/**
 * Zahnfee-EINSTELLUNGEN (aktiv, Modell, Uhrzeit, Lookback, Quellen, Soul).
 * Aus der ZahnfeePage herausgelöst — die Auswertung (Briefing) bleibt dort,
 * die Settings leben jetzt im zentralen Settings-Hub. Trennung von Auswertung
 * und Einstellung (Tills Vorgabe).
 */
export function ZahnfeeConfig() {
  const { t } = useTranslation("zahnfee")
  const [cfg, setCfg] = useState<Cfg | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    zahnfeeApi.config().then(setCfg).catch(() => {})
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

  if (!cfg) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 size={20} className="animate-spin text-zinc-500" />
      </div>
    )
  }

  return (
    <div className="max-w-2xl flex flex-col gap-5">
      <label className="flex items-center gap-3 cursor-pointer">
        <input type="checkbox" checked={cfg.enabled}
          onChange={(e) => setCfg({ ...cfg, enabled: e.target.checked })}
          className="w-4 h-4 accent-violet-500" />
        <span className="text-sm text-zinc-300">{t("config.enabled")}</span>
      </label>

      <div className="flex flex-col gap-1.5">
        <label className="text-xs text-zinc-500 font-medium uppercase tracking-wider">{t("config.model")}</label>
        <ModelPicker current={cfg.model} hint={t("config.model_hint")} showReset
          onPick={(m) => setCfg({ ...cfg, model: m })}
          onReset={() => setCfg({ ...cfg, model: "" })} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-xs text-zinc-500 font-medium uppercase tracking-wider">{t("config.run_hour")}</label>
          <input type="number" min={0} max={23} value={cfg.run_hour}
            onChange={(e) => setCfg({ ...cfg, run_hour: Number(e.target.value) })}
            className="bg-zinc-800 border border-white/[8%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-violet-500/50" />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-xs text-zinc-500 font-medium uppercase tracking-wider">{t("config.lookback")}</label>
          <input type="number" min={1} max={720} value={cfg.lookback_hours}
            onChange={(e) => setCfg({ ...cfg, lookback_hours: Number(e.target.value) })}
            className="bg-zinc-800 border border-white/[8%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-violet-500/50" />
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-xs text-zinc-500 font-medium uppercase tracking-wider">{t("config.sources")}</label>
        <label className="flex items-center gap-3 cursor-pointer">
          <input type="checkbox" checked={cfg.source_datamining}
            onChange={(e) => setCfg({ ...cfg, source_datamining: e.target.checked })}
            className="w-4 h-4 accent-violet-500" />
          <span className="text-sm text-zinc-300">{t("config.source_datamining")}</span>
        </label>
        <label className="flex items-center gap-3 cursor-pointer opacity-50">
          <input type="checkbox" checked={cfg.source_mail}
            onChange={(e) => setCfg({ ...cfg, source_mail: e.target.checked })}
            className="w-4 h-4 accent-violet-500" />
          <span className="text-sm text-zinc-300">{t("config.source_mail")} <span className="text-zinc-600 text-xs">{t("config.source_mail_unavailable")}</span></span>
        </label>
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <label className="text-xs text-zinc-500 font-medium uppercase tracking-wider">{t("config.soul")}</label>
          <button onClick={() => setCfg({ ...cfg, soul: "" })}
            className="flex items-center gap-1 text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
            title={t("config.soul_reset")}>
            <RotateCcw size={11} /> {t("config.soul_reset_short")}
          </button>
        </div>
        <textarea value={cfg.soul} onChange={(e) => setCfg({ ...cfg, soul: e.target.value })} rows={12}
          className="bg-zinc-800 border border-white/[8%] rounded-lg px-3 py-2 text-sm text-zinc-200 font-mono resize-y focus:outline-none focus:border-violet-500/50 leading-relaxed" />
      </div>

      <button onClick={save} disabled={saving}
        className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white text-sm font-medium transition-colors">
        {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
        {saved ? t("config.saved") : saving ? t("config.saving") : t("config.save")}
      </button>
    </div>
  )
}
