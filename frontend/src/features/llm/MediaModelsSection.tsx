import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { catalogApi, type CatalogModel } from "./api"

type Side = "output" | "input"

interface Category {
  key: string
  labelKey: string
  side: Side
  modality: string
}

// Musik und TTS teilen sich Audio-Output — die Kategorie filtert nur auf
// audio-fähige Modelle, die richtige Wahl (Lyria vs. gpt-audio) trifft der Mensch.
const CATEGORIES: Category[] = [
  { key: "image", labelKey: "media_models.image", side: "output", modality: "image" },
  { key: "music", labelKey: "media_models.music", side: "output", modality: "audio" },
  { key: "tts", labelKey: "media_models.tts", side: "output", modality: "audio" },
]

function matches(model: CatalogModel, cat: Category): boolean {
  const mods = cat.side === "output" ? model.output_modalities : model.input_modalities
  return (mods ?? []).includes(cat.modality)
}

interface MediaModelsSectionProps {
  mediaModels: Record<string, string>
  onChange: (category: string, model: string) => void
}

export function MediaModelsSection({ mediaModels, onChange }: MediaModelsSectionProps) {
  const { t } = useTranslation("llm")
  const { t: tCommon } = useTranslation("common")
  const [models, setModels] = useState<CatalogModel[]>([])

  useEffect(() => {
    catalogApi.get()
      .then((res) => setModels(res.providers.flatMap((p) => p.models)))
      .catch(() => {})
  }, [])

  const hasAny = CATEGORIES.some((cat) => models.some((m) => matches(m, cat)))

  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
        {t("media_models.title")}
      </p>
      {!hasAny && <p className="text-[11px] text-zinc-600">{t("media_models.none")}</p>}
      {CATEGORIES.map((cat) => {
        const candidates = models.filter((m) => matches(m, cat))
        if (candidates.length === 0) return null
        return (
          <div key={cat.key} className="space-y-1">
            <label className="text-[11px] text-zinc-500">{t(cat.labelKey)}</label>
            <select value={mediaModels[cat.key] ?? ""}
              onChange={(e) => onChange(cat.key, e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg bg-zinc-900 border border-white/[8%] text-zinc-200 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500/50">
              <option value="" className="bg-zinc-900 text-zinc-400">{tCommon("actions.select")}</option>
              {candidates.map((m) => (
                <option key={m.id} value={m.id} className="bg-zinc-900 text-zinc-200">{m.id}</option>
              ))}
            </select>
          </div>
        )
      })}
      <p className="text-[11px] text-zinc-600">{t("media_models.hint")}</p>
    </div>
  )
}
