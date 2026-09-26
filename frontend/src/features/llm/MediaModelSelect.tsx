import { useMemo } from "react"

export interface MediaModel {
  id: string
  name?: string
  provider?: string
  local?: boolean
}

interface Props {
  label: string
  value: string
  models: MediaModel[]
  onChange: (model: string) => void
}

/**
 * Auswahl für Bild/Video: eine Modell-ID ist zugleich die Routing-Entscheidung.
 * Cloud-IDs gehen an OpenRouter, `local:`-IDs an einen freigegebenen ComfyUI-
 * Workflow. Die Gruppierung macht diese Sicherheits- und Kosten-Grenze sichtbar,
 * ohne einen zweiten, widersprüchlichen "Provider"-Wert zu speichern.
 */
export function MediaModelSelect({ label, value, models, onChange }: Props) {
  const groups = useMemo(() => {
    const cloud = models.filter((model) => !model.local)
    const local = new Map<string, MediaModel[]>()
    for (const model of models) {
      if (!model.local) continue
      const provider = model.provider || "Lokale GPU (ComfyUI)"
      local.set(provider, [...(local.get(provider) ?? []), model])
    }
    return { cloud, local: [...local.entries()] }
  }, [models])

  return (
    <div className="space-y-1">
      <label className="text-[11px] text-zinc-500">{label}</label>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full px-3 py-2.5 rounded-lg bg-zinc-900 border border-white/[8%] text-zinc-200 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500/50"
      >
        <option value="" className="bg-zinc-900 text-zinc-400">Automatisch (Cloud-Standard)</option>
        {groups.cloud.length > 0 && (
          <optgroup label="Cloud · OpenRouter" className="bg-zinc-900 text-zinc-400">
            {groups.cloud.map((model) => (
              <option key={model.id} value={model.id} className="bg-zinc-900 text-zinc-200">
                {model.name || model.id}
              </option>
            ))}
          </optgroup>
        )}
        {groups.local.map(([provider, localModels]) => (
          <optgroup key={provider} label={`Diese WKS · ${provider}`} className="bg-zinc-900 text-zinc-400">
            {localModels.map((model) => (
              <option key={model.id} value={model.id} className="bg-zinc-900 text-zinc-200">
                {model.name || model.id}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </div>
  )
}
