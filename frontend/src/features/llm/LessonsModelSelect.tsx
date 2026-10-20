import { useTranslation } from "react-i18next"
import type { RegistryModel } from "./api"
import { providerName } from "./_llm_providers"
import { LESSONS_OFF } from "./lessonsModel"

interface Props {
  value: string
  models: RegistryModel[]
  onChange: (choice: string) => void
}

/** Auswahl „Lehren“: Standard (wie Chat), ein Textmodell oder Aus. Eigene Auswahl, weil „leer“ hier eine Bedeutung hat. */
export function LessonsModelSelect({ value, models, onChange }: Props) {
  const { t } = useTranslation("llm")
  const sorted = [...models].sort((a, b) => `${providerName(a.provider)} ${a.label}`.localeCompare(`${providerName(b.provider)} ${b.label}`))
  const known = value === "" || value === LESSONS_OFF || sorted.some((m) => m.id === value)
  return (
    <div className="space-y-1">
      <label className="text-[11px] text-zinc-500">{t("default_models.lessons")}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)} aria-label={t("default_models.lessons")}
        className="w-full px-3 py-2.5 rounded-lg bg-zinc-900 border border-white/[8%] text-zinc-200 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500/50">
        <option value="" className="bg-zinc-900">{t("default_models.lessons_default")}</option>
        <option value={LESSONS_OFF} className="bg-zinc-900">{t("default_models.lessons_off")}</option>
        {!known && <option value={value} className="bg-zinc-900">{value}</option>}
        {sorted.map((m) => (
          <option key={m.id} value={m.id} className="bg-zinc-900">{providerName(m.provider)} · {m.label}</option>
        ))}
      </select>
      <p className="text-[11px] text-zinc-500">{t("default_models.lessons_hint")}</p>
    </div>
  )
}
