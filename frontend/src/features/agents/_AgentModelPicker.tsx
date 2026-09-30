import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import type { RegistryModel } from "@/features/llm/api"
import { groupModels, providersOf } from "./_modelGroups"

const control = "px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"

/** Hauptmodell im Agent-Editor: Suche, Anbieter-Filter, „nur gratis“,
 *  Liste nach Anbieter gruppiert und ohne Limit (Task 19687316). */
export function AgentModelPicker({ value, catalog, onChange }: {
  value: string; catalog: RegistryModel[]; onChange: (m: string) => void
}) {
  const { t } = useTranslation("agents")
  const [query, setQuery] = useState("")
  const [provider, setProvider] = useState("")
  const [onlyFree, setOnlyFree] = useState(false)
  const providers = useMemo(() => providersOf(catalog), [catalog])
  const groups = useMemo(
    () => groupModels(catalog, { query, onlyFree, provider }),
    [catalog, query, onlyFree, provider],
  )
  const shown = groups.reduce((n, g) => n + g.models.length, 0)
  const valueVisible = groups.some((g) => g.models.some((m) => m.id === value))

  return (
    <div className="space-y-1">
      <div className="flex flex-wrap gap-2">
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("model_picker.search")}
          className={`${control} flex-1 min-w-[140px]`} />
        <select value={provider} onChange={(e) => setProvider(e.target.value)} className={control}
          aria-label={t("model_picker.all_providers")}>
          <option value="">{t("model_picker.all_providers")}</option>
          {providers.map((p) => <option key={p.provider} value={p.provider}>{p.name} ({p.count})</option>)}
        </select>
        <label className="flex items-center gap-1 text-[10px] text-zinc-400 whitespace-nowrap">
          <input type="checkbox" checked={onlyFree} onChange={(e) => setOnlyFree(e.target.checked)} />
          {t("model_picker.only_free")}
        </label>
      </div>
      <select value={value} onChange={(e) => onChange(e.target.value)} size={8}
        className={`w-full ${control} font-mono`}>
        {!valueVisible && value && <option value={value}>{value} {t("model_picker.current")}</option>}
        {groups.map((g) => (
          <optgroup key={g.provider} label={`${g.name} (${g.models.length})`}>
            {g.models.map((m) => (
              <option key={m.id} value={m.id}>{m.is_free === true ? "🆓 " : ""}{m.id}</option>
            ))}
          </optgroup>
        ))}
      </select>
      <p className="text-[10px] text-zinc-600">
        {shown === 0 ? t("model_picker.none") : t("model_picker.count", { shown, total: catalog.length })}
      </p>
    </div>
  )
}
