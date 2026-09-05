import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { llmApi, llmModelsApi, type LlmConfig, type MediaModel, type RegistryModel } from "./api"
import { MediaModelSelect } from "./MediaModelSelect"
import { KNOWN_PROVIDERS } from "./_llm_providers"

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

interface ModelSelectProps {
  label: string
  value: string
  models: RegistryModel[]
  onChange: (model: string) => void
}

function providerName(provider: string): string {
  return KNOWN_PROVIDERS.find((p) => p.id === provider)?.name ?? provider
}

function ModelSelect({ label, value, models, onChange }: ModelSelectProps) {
  const { t: tCommon } = useTranslation("common")
  const { t } = useTranslation("llm")
  const grouped = models.reduce<Record<string, RegistryModel[]>>((acc, model) => {
    const provider = model.provider || "unknown"
    const list = acc[provider] ?? []
    list.push(model)
    acc[provider] = list
    return acc
  }, {})
  const groups = Object.entries(grouped)
    .sort(([a], [b]) => providerName(a).localeCompare(providerName(b)))

  function costLabel(model: RegistryModel): string {
    if (model.provider === "ollama") return t("default_models.local")
    if (model.is_free === true) return t("default_models.free")
    if (model.is_free === false) return t("default_models.paid")
    return t("default_models.cost_unknown")
  }

  return (
    <div className="space-y-1">
      <label className="text-[11px] text-zinc-500">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2.5 rounded-lg bg-zinc-900 border border-white/[8%] text-zinc-200 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500/50"
      >
        <option value="" className="bg-zinc-900 text-zinc-400">{tCommon("actions.select")}</option>
        {groups.map(([provider, providerModels]) => (
          <optgroup key={provider} label={providerName(provider)} className="bg-zinc-900 text-zinc-400">
            {[...providerModels]
              .sort((a, b) => a.label.localeCompare(b.label))
              .map((model) => (
                <option key={model.id} value={model.id} className="bg-zinc-900 text-zinc-200">
                  {providerName(provider)} · {model.label} · {costLabel(model)}
                </option>
              ))}
          </optgroup>
        ))}
      </select>
    </div>
  )
}

interface DefaultModelsSectionProps {
  config: LlmConfig
  onSaved: () => void
}

export function DefaultModelsSection({ config, onSaved }: DefaultModelsSectionProps) {
  const { t } = useTranslation("llm")
  const [modelsByPurpose, setModelsByPurpose] = useState<Partial<Record<Purpose, RegistryModel[]>>>({})
  const [mediaModels, setMediaModels] = useState<Partial<Record<"image" | "video", MediaModel[]>>>({})
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const purposes: Purpose[] = ["chat", "embed", "image", "music", "tts", "stt", "video"]
    Promise.all(
      purposes.map((p) =>
        llmModelsApi.byModality(p)
          .then((res) => ({ purpose: p, models: res.models }))
          .catch(() => ({ purpose: p, models: [] as RegistryModel[] }))
      )
    ).then((results) => {
      const map: Partial<Record<Purpose, RegistryModel[]>> = {}
      for (const r of results) map[r.purpose] = r.models
      setModelsByPurpose(map)
    })
    Promise.all(["image", "video"].map((category) =>
      llmModelsApi.media(category as "image" | "video")
        .then((res) => ({ category: category as "image" | "video", models: res.models }))
        .catch(() => ({ category: category as "image" | "video", models: [] as MediaModel[] }))
    )).then((results) => {
      const map: Partial<Record<"image" | "video", MediaModel[]>> = {}
      for (const result of results) map[result.category] = result.models
      setMediaModels(map)
    })
  }, [])

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
        const value = def.getVal(config)
        if (def.purpose === "image" || def.purpose === "video") {
          return (
            <MediaModelSelect
              key={def.purpose}
              label={t(def.labelKey)}
              value={value}
              models={mediaModels[def.purpose] ?? []}
              onChange={(model) => handleChange(def, model)}
            />
          )
        }
        return (
          <ModelSelect
            key={def.purpose}
            label={t(def.labelKey)}
            value={value}
            models={modelsByPurpose[def.purpose] ?? []}
            onChange={(model) => handleChange(def, model)}
          />
        )
      })}
    </div>
  )
}
