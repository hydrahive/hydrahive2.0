import { useTranslation } from "react-i18next"
import type { RegistryModel } from "@/features/llm/api"
import { ModelSelect } from "@/features/llm/ModelSelect"
import { padChain, sameProviderSteps } from "./templateLogic"

const STEP_KEYS = ["primary", "failover", "emergency"] as const

/** Drei Stufen der Modellkette. Alle Modelle aller Anbieter (inkl. lokaler Ollama-Modelle), ohne Limit. */
export function TemplateChain({ chain, models, readOnly, onChange }: {
  chain: string[]; models: RegistryModel[]; readOnly: boolean; onChange: (chain: string[]) => void
}) {
  const { t } = useTranslation("llm")
  const steps = padChain(chain)
  const known = new Set(models.map((m) => m.id))

  function set(i: number, model: string) {
    const next = [...steps]
    next[i] = model
    onChange(next)
  }

  return (
    <div className="space-y-2">
      <div className="grid gap-3 md:grid-cols-3">
        {steps.map((model, i) => (
          <div key={i} className="rounded-[4px] border border-white/[8%] bg-white/[2%] p-2">
            {readOnly
              ? <div className="space-y-1">
                  <p className="text-[11px] text-zinc-500">{t(`templates.chain.${STEP_KEYS[i]}`)}</p>
                  <p className="text-sm text-zinc-200 break-all">{model || "—"}</p>
                </div>
              : <ModelSelect label={t(`templates.chain.${STEP_KEYS[i]}`)} value={model} models={models}
                  onChange={(m) => set(i, m)} />}
            {model && models.length > 0 && !known.has(model) && (
              <p className="mt-1 text-[11px] text-rose-400">{t("templates.chain.unknown")}</p>
            )}
          </div>
        ))}
      </div>
      {sameProviderSteps(steps) && (
        <p className="text-xs text-amber-400">{t("templates.chain.same_provider")}</p>
      )}
    </div>
  )
}
