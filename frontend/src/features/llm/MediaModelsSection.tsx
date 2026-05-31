import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { catalogApi, llmApi, type CatalogModel, type SpeechModel } from "./api"

interface Category {
  key: string
  labelKey: string
  modality: string  // output-Modalität im Chat-Katalog
}

// Bild/Musik kommen aus dem Chat-Katalog (output-Modalität). TTS NICHT — echte
// Speech-Modelle (output:speech) liegen auf eigener Fläche (/llm/speech-models).
const CATALOG_CATEGORIES: Category[] = [
  { key: "image", labelKey: "media_models.image", modality: "image" },
  { key: "music", labelKey: "media_models.music", modality: "audio" },
]

interface MediaModelsSectionProps {
  mediaModels: Record<string, string>
  onChange: (category: string, model: string) => void
}

function Select({ label, value, options, onChange }: {
  label: string; value: string; options: string[]; onChange: (v: string) => void
}) {
  const { t: tCommon } = useTranslation("common")
  return (
    <div className="space-y-1">
      <label className="text-[11px] text-zinc-500">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2.5 rounded-lg bg-zinc-900 border border-white/[8%] text-zinc-200 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500/50">
        <option value="" className="bg-zinc-900 text-zinc-400">{tCommon("actions.select")}</option>
        {options.map((o) => <option key={o} value={o} className="bg-zinc-900 text-zinc-200">{o}</option>)}
      </select>
    </div>
  )
}

export function MediaModelsSection({ mediaModels, onChange }: MediaModelsSectionProps) {
  const { t } = useTranslation("llm")
  const [catalog, setCatalog] = useState<CatalogModel[]>([])
  const [speech, setSpeech] = useState<SpeechModel[]>([])

  useEffect(() => {
    catalogApi.get()
      .then((res) => setCatalog(res.providers.flatMap((p) => p.models)))
      .catch(() => {})
    llmApi.getSpeechModels().then(setSpeech).catch(() => {})
  }, [])

  const catalogOptions = (modality: string) =>
    catalog.filter((m) => (m.output_modalities ?? []).includes(modality)).map((m) => m.id)

  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
        {t("media_models.title")}
      </p>
      {CATALOG_CATEGORIES.map((cat) => {
        const options = catalogOptions(cat.modality)
        if (options.length === 0) return null
        return (
          <Select key={cat.key} label={t(cat.labelKey)} options={options}
            value={mediaModels[cat.key] ?? ""}
            onChange={(v) => onChange(cat.key, v)} />
        )
      })}
      {speech.length > 0 && (
        <Select label={t("media_models.tts")} options={speech.map((s) => s.id)}
          value={mediaModels["tts"] ?? ""}
          onChange={(v) => onChange("tts", v)} />
      )}
      <p className="text-[11px] text-zinc-600">{t("media_models.hint")}</p>
    </div>
  )
}
