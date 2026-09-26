import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { llmApi, llmModelsApi, type LlmConfig, type MediaModel, type RegistryModel } from "./api"
import { MediaModelSelect } from "./MediaModelSelect"
import { ModelSelect } from "./ModelSelect"

// Maps purpose → config field path (mirrors backend _PURPOSE_KEYS)
type Purpose = "chat" | "embed" | "image" | "music" | "tts" | "stt" | "video"

interface PurposeDef {
  purpose: Purpose
  labelKey: string
  getVal: (cfg: LlmConfig) => string
  setVal: (cfg: LlmConfig, model: string) => LlmConfig
}

const PURPOSES: PurposeDef[] = [
  {
    purpose: "chat",
    labelKey: "default_models.chat",
    getVal: (cfg) => cfg.default_model ?? "",
    setVal: (cfg, model) => ({ ...cfg, default_model: model }),
  },
  {
    purpose: "embed",
    labelKey: "default_models.embed",
    getVal: (cfg) => cfg.embed_model ?? "",
    setVal: (cfg, model) => ({ ...cfg, embed_model: model }),
  },
  {
    purpose: "image",
    labelKey: "default_models.image",
    getVal: (cfg) => cfg.media_models?.image ?? "",
    setVal: (cfg, model) => ({ ...cfg, media_models: { ...(cfg.media_models ?? {}), image: model } }),
  },
  {
    purpose: "music",
    labelKey: "default_models.music",
    getVal: (cfg) => cfg.media_models?.music ?? "",
    setVal: (cfg, model) => ({ ...cfg, media_models: { ...(cfg.media_models ?? {}), music: model } }),
  },
  {
    purpose: "tts",
    labelKey: "default_models.tts",
    getVal: (cfg) => cfg.media_models?.tts ?? "",
    setVal: (cfg, model) => ({ ...cfg, media_models: { ...(cfg.media_models ?? {}), tts: model } }),
  },
  {
    purpose: "stt",
    labelKey: "default_models.stt",
    getVal: (cfg) => cfg.media_models?.transcribe ?? "",
    setVal: (cfg, model) => ({ ...cfg, media_models: { ...(cfg.media_models ?? {}), transcribe: model } }),
  },
  {
    purpose: "video",
    labelKey: "default_models.video",
    getVal: (cfg) => cfg.media_models?.video ?? "",
    setVal: (cfg, model) => ({ ...cfg, media_models: { ...(cfg.media_models ?? {}), video: model } }),
  },
]

interface DefaultModelsSectionProps {
  config: LlmConfig
  onSaved: () => void
}

export function DefaultModelsSection({ config, onSaved }: DefaultModelsSectionProps) {
  const { t } = useTranslation("llm")
  const [modelsByPurpose, setModelsByPurpose] = useState<Partial<Record<Purpose, RegistryModel[]>>>({})
  const [mediaModels, setMediaModels] = useState<Partial<Record<"image" | "video", MediaModel[]>>>({})
  // Vom Backend gelieferte Listen-ID zum gespeicherten Wert (siehe api.ts).
  const [selectedByPurpose, setSelectedByPurpose] = useState<Partial<Record<Purpose, string>>>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const purposes: Purpose[] = ["chat", "embed", "image", "music", "tts", "stt", "video"]
    Promise.all(
      purposes.map((p) =>
        llmModelsApi.byModality(p)
          .then((res) => ({ purpose: p, models: res.models, selected: res.selected ?? "" }))
          .catch(() => ({ purpose: p, models: [] as RegistryModel[], selected: "" }))
      )
    ).then((results) => {
      const map: Partial<Record<Purpose, RegistryModel[]>> = {}
      const sel: Partial<Record<Purpose, string>> = {}
      for (const r of results) { map[r.purpose] = r.models; sel[r.purpose] = r.selected }
      setModelsByPurpose(map)
      setSelectedByPurpose((prev) => ({ ...prev, ...sel }))
    })
    Promise.all(["image", "video"].map((category) =>
      llmModelsApi.media(category as "image" | "video")
        .then((res) => ({ category: category as "image" | "video", models: res.models, selected: res.selected ?? "" }))
        .catch(() => ({ category: category as "image" | "video", models: [] as MediaModel[], selected: "" }))
    )).then((results) => {
      const map: Partial<Record<"image" | "video", MediaModel[]>> = {}
      const sel: Partial<Record<Purpose, string>> = {}
      for (const result of results) { map[result.category] = result.models; sel[result.category] = result.selected }
      setMediaModels(map)
      setSelectedByPurpose((prev) => ({ ...prev, ...sel }))
    })
  }, [])

  // Was die Auswahl anzeigen soll: exakt gespeicherter Wert, wenn er in der
  // Liste steht; sonst die vom Backend abgeglichene Listen-ID. Nach einer
  // Änderung in der Auswahl ist der neue Wert immer eine Listen-ID.
  function displayValue(def: PurposeDef, listed: { id: string }[]): string {
    const value = def.getVal(config)
    if (!value || listed.some((m) => m.id === value)) return value
    return selectedByPurpose[def.purpose] || value
  }

  async function handleChange(def: PurposeDef, model: string) {
    setError(null)
    const updated = def.setVal(config, model)
    try {
      await llmApi.updateConfig(updated)
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : t("default_models.save_error"))
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
        {t("default_models.title")}
      </p>
      {error && (
        <p className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2">
          {error}
        </p>
      )}
      {PURPOSES.map((def) => {
        if (def.purpose === "image" || def.purpose === "video") {
          const listed = mediaModels[def.purpose] ?? []
          return (
            <MediaModelSelect
              key={def.purpose}
              label={t(def.labelKey)}
              value={displayValue(def, listed)}
              models={listed}
              onChange={(model) => handleChange(def, model)}
            />
          )
        }
        const listed = modelsByPurpose[def.purpose] ?? []
        return (
          <ModelSelect
            key={def.purpose}
            label={t(def.labelKey)}
            value={displayValue(def, listed)}
            models={listed}
            onChange={(model) => handleChange(def, model)}
          />
        )
      })}
    </div>
  )
}
