import { useTranslation } from "react-i18next"
import { AdminFeedback } from "@/features/cockpit/admin/ui"

/** Werkzeuge ohne Bereich (Spec 4.7): nur die Liste und der Hinweis. Eine Zuordnung per Klick gibt es nicht; das Modul meldet sie selbst. */
export function UnassignedTools({ tools }: { tools: string[] }) {
  const { t } = useTranslation("agents")
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-bold text-[#e8eef8]">{t("areas.unassigned_title")}</h3>
      <p className="text-xs text-[#9aa7bc]">{t("areas.unassigned_hint")}</p>
      {tools.length === 0
        ? <AdminFeedback tone="success">{t("areas.unassigned_none")}</AdminFeedback>
        : <ul className="flex flex-wrap gap-1.5">{tools.map((n) => (
          <li key={n} className="rounded-[4px] border border-s-rand bg-s-innen px-2 py-1 font-mono text-xs text-[#e8eef8]">{n}</li>))}
        </ul>}
    </section>
  )
}
