import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { templatesApi } from "@/features/llm/templates/api"
import type { AgentTemplate } from "@/features/llm/templates/types"
import { groupTemplates } from "@/features/llm/templates/templateLogic"

const control = "w-full px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200"

/** Template-Auswahl im Agent-Editor (Spec agent-templates.md Kap. 10). Gebunden: Werte nur lesend. */
export function TemplateBinding({ value, onChange }: { value: string | null | undefined; onChange: (t: string) => void }) {
  const { t } = useTranslation("agents")
  const { t: tLlm } = useTranslation("llm")
  const [list, setList] = useState<AgentTemplate[]>([])
  useEffect(() => { templatesApi.list().then((r) => setList(r.templates)).catch(() => setList([])) }, [])
  const current = list.find((x) => x.id === value)

  return (
    <div className="space-y-2 rounded-md border border-white/[8%] bg-white/[2%] p-2">
      <label className="block text-[10px] font-medium text-zinc-500">{t("template.label")}</label>
      <select value={value ?? ""} onChange={(e) => onChange(e.target.value)} className={control}>
        {!value && <option value="">{t("template.none")}</option>}
        {groupTemplates(list).map(({ group, items }) => (
          <optgroup key={group} label={tLlm(`templates.groups.${group}`)}>
            {items.map((x) => <option key={x.id} value={x.id}>{x.label}</option>)}
          </optgroup>
        ))}
      </select>
      {current
        ? <TemplateSummary tpl={current} />
        : <p className="text-[10px] text-amber-400">{value ? t("template.unknown") : t("template.unbound_hint")}</p>}
    </div>
  )
}

export function TemplateSummary({ tpl }: { tpl: AgentTemplate }) {
  const { t } = useTranslation("agents")
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[11px]">
      <dt className="text-zinc-500">{t("template.chain")}</dt>
      <dd className="break-all text-zinc-300">{tpl.chain.join(" → ") || "—"}</dd>
      <dt className="text-zinc-500">{t("template.budget")}</dt>
      <dd className="text-zinc-300">
        {t("template.budget_value", { it: tpl.budget.max_iterations, tok: tpl.budget.max_tokens,
          sec: tpl.budget.timeout_seconds })}
      </dd>
      <dt className="text-zinc-500" />
      <dd className="text-zinc-500">{t("template.managed_hint")}</dd>
    </dl>
  )
}
