import { useTranslation } from "react-i18next"
import { groupTemplates } from "./templateLogic"
import type { AgentTemplate, HealthState } from "./types"

const DOT: Record<HealthState, string> = { green: "bg-emerald-400", yellow: "bg-amber-400", red: "bg-rose-500" }

/** Linke Liste: Templates nach Gruppe, mit Ampel und Anzahl gebundener Agenten. */
export function TemplateList({ templates, selected, onSelect }: {
  templates: AgentTemplate[]; selected: string | null; onSelect: (id: string) => void
}) {
  const { t } = useTranslation("llm")
  return (
    <nav className="space-y-3" aria-label={t("templates.title")}>
      {groupTemplates(templates).map(({ group, items }) => (
        <div key={group}>
          <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-widest text-[#9aa7bc]">
            {t(`templates.groups.${group}`)}
          </p>
          {items.map((tpl) => (
            <button key={tpl.id} type="button" onClick={() => onSelect(tpl.id)}
              className={`flex w-full items-center gap-2 rounded-[4px] px-2 py-1.5 text-left text-sm transition-colors ${
                selected === tpl.id ? "bg-white/[8%] text-[#e8eef8]" : "text-[#9aa7bc] hover:bg-white/5"}`}>
              <span className={`h-2 w-2 shrink-0 rounded-full ${DOT[tpl.health?.state ?? "red"]}`}
                title={t(`templates.health.${tpl.health?.state ?? "red"}`)} />
              <span className="flex-1 truncate">{tpl.label}</span>
              <span className="text-[11px] tabular-nums text-zinc-500">{tpl.bound_count ?? 0}</span>
            </button>
          ))}
        </div>
      ))}
    </nav>
  )
}
