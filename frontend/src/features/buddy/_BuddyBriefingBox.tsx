import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Loader2 } from "lucide-react"
import { Link } from "react-router-dom"
import { CockpitPanel } from "@/features/cockpit/CockpitPanel"
import { zahnfeeApi, type Briefing } from "@/features/zahnfee/api"

/**
 * Morgen-Briefing der Zahnfee im Buddy (war seit d041b2cf nirgends sichtbar).
 * Reines Lesen des eigenen Briefings — kein LLM-Aufruf.
 */
export function BuddyBriefingBox({ isAdmin }: { isAdmin: boolean }) {
  const { t } = useTranslation("buddy")
  const [briefing, setBriefing] = useState<Briefing | null | undefined>(undefined)

  useEffect(() => {
    let alive = true
    zahnfeeApi.briefing()
      .then((r) => { if (alive) setBriefing(r.briefing) })
      .catch(() => { if (alive) setBriefing(null) })
    return () => { alive = false }
  }, [])

  const sections = briefing ? [
    { label: t("briefing.open"), value: briefing.open_items, color: "text-amber-300" },
    { label: t("briefing.went_well"), value: briefing.went_well, color: "text-emerald-300" },
    { label: t("briefing.went_badly"), value: briefing.went_badly, color: "text-rose-300" },
    { label: t("briefing.today"), value: briefing.today, color: "text-[#69d7ff]" },
  ].filter((s) => s.value) : []

  return (
    <CockpitPanel title={t("boxes.zahnfee")} eyebrow={briefing?.date ?? "Briefing"}>
      {briefing === undefined ? (
        <Loader2 size={14} className="animate-spin text-[#8d9ab0]" />
      ) : !briefing ? (
        <p className="text-xs leading-4 text-[#8d9ab0]">
          {t("left_panel.no_briefing")}
          {isAdmin ? <> <Link to="/zahnfee" className="text-[#69d7ff] hover:underline">{t("left_panel.setup")}</Link></> : null}
        </p>
      ) : briefing.error ? (
        <p className="text-xs text-rose-300">{briefing.error}</p>
      ) : (
        <div className="space-y-2">
          {sections.map((s) => (
            <div key={s.label}>
              <p className={`text-[10px] font-semibold uppercase tracking-wider ${s.color}`}>{s.label}</p>
              <p className="whitespace-pre-line text-xs leading-snug text-[#c9d3e3] line-clamp-4">{s.value}</p>
            </div>
          ))}
        </div>
      )}
    </CockpitPanel>
  )
}
