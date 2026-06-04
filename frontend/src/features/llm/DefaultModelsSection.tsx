import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { llmApi, llmModelsApi, type LlmConfig, type RegistryModel } from "./api"

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

function ModelSelect({ label, value, models, onChange }: ModelSelectProps) {
  const { t: tCommon } = useTranslation("common")
  return (
    <div className="space-y-1">
      <label className="text-[11px] text-zinc-500">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2.5 rounded-lg bg-zinc-900 border border-white/[8%] text-zinc-200 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500/50"
      >
        <option value="" className="bg-zinc-900 text-zinc-400">{tCommon("actions.select")}</option>
        {models.map((m) => (
          <option key={m.id} value={m.id} className="bg-zinc-900 text-zinc-200">
            {m.label}
          </option>
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
        const models = modelsByPurpose[def.purpose] ?? []
        return (
          <ModelSelect
            key={def.purpose}
            label={t(def.labelKey)}
            value={def.getVal(config)}
            models={models}
            onChange={(model) => handleChange(def, model)}
          />
        )
      })}
    </div>
  )
}
