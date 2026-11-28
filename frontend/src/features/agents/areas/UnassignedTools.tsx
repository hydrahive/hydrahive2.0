import { useTranslation } from "react-i18next"
import { AdminFeedback } from "@/features/cockpit/admin/ui"
import type { UnassignedTool } from "./areasApi"

/** Werkzeuge ohne Bereich (Spec 4.7): Liste mit Modul und Beschreibung, nach Modul gruppiert. Keine Zuordnung per Klick –
 *  das Modul meldet seinen Bereich selbst. Tool-Namen nur in der Expertenansicht (Review #795). */
export function UnassignedTools({ tools, expert = false }: { tools: UnassignedTool[]; expert?: boolean }) {
  const { t } = useTranslation("agents")
  const byModule = new Map<string, UnassignedTool[]>()
  for (const tool of tools) byModule.set(tool.module || "–", [...(byModule.get(tool.module || "–") ?? []), tool])
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-bold text-[#e8eef8]">{t("areas.unassigned_title")}</h3>
      <p className="text-xs text-[#9aa7bc]">{t("areas.unassigned_hint")}</p>
      {tools.length === 0
        ? <AdminFeedback tone="success">{t("areas.unassigned_none")}</AdminFeedback>
        : [...byModule.entries()].map(([mod, list]) => (
          <div key={mod} className="rounded-[4px] border border-s-rand bg-s-innen px-3 py-2" data-testid="unassigned-module">
            <p className="text-xs font-bold text-[#e8eef8]">{t("areas.unassigned_module", { module: mod, count: list.length })}</p>
            <ul className="mt-1 space-y-0.5">
              {list.map((tool) => (
                <li key={tool.name} className="text-xs text-[#9aa7bc]">
                  {tool.description || t("areas.unassigned_no_description")}
                  {expert && <span className="ml-1 font-mono text-[#e8eef8]">({tool.name})</span>}
                </li>
              ))}
            </ul>
          </div>
        ))}
    </section>
  )
}
