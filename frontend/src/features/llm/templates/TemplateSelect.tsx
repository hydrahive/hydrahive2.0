import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { templatesApi } from "./api"
import { groupTemplates } from "./templateLogic"
import type { AgentTemplate, TemplateGroup } from "./types"

/** Auswahl eines Agenten-Templates (gruppiert). Gemeinsam für Agent-Editor, Projekt anlegen, Neuer Agent.
 *  `groups` grenzt die Auswahl ein (z. B. nur Spezialisten). */
export function TemplateSelect({ value, onChange, groups, className, id }: {
  value: string; onChange: (id: string) => void; groups?: TemplateGroup[]; className?: string; id?: string
}) {
  const { t } = useTranslation("llm")
  const [list, setList] = useState<AgentTemplate[]>([])
  useEffect(() => { templatesApi.list().then((r) => setList(r.templates)).catch(() => setList([])) }, [])
  const shown = groupTemplates(groups ? list.filter((x) => groups.includes(x.group)) : list)
  return (
    <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className={className}>
      {!list.some((x) => x.id === value) && <option value={value}>{value || "—"}</option>}
      {shown.map(({ group, items }) => (
        <optgroup key={group} label={t(`templates.groups.${group}`)}>
          {items.map((x) => <option key={x.id} value={x.id}>{x.label} · {x.chain[0] ?? "—"}</option>)}
        </optgroup>
      ))}
    </select>
  )
}
