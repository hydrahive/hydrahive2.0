import { useTranslation } from "react-i18next"
import type { RegistryModel } from "./api"
import { KNOWN_PROVIDERS } from "./_llm_providers"

interface ModelSelectProps {
  label: string
  value: string
  models: RegistryModel[]
  onChange: (model: string) => void
}

function providerName(provider: string): string {
  // "local" = Dienste auf diesem Server (Whisper/Piper), kein konfigurierter Anbieter.
  if (provider === "local") return "Dieser Server (lokal)"
  return KNOWN_PROVIDERS.find((p) => p.id === provider)?.name ?? provider
}

/** Auswahl aus der Registry-Liste, gruppiert nach Anbieter. */
export function ModelSelect({ label, value, models, onChange }: ModelSelectProps) {
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
    if (model.provider === "ollama" || model.provider === "local") return t("default_models.local")
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
