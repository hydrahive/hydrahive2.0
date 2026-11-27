import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { AdminFeedback } from "@/features/cockpit/admin/ui"
import { api } from "@/shared/api-client"

export interface AuditEntry { at: string; actor: string; action: string; target: string; areas: string[]; tools: string[]; unknown: string[] }

/** Protokoll in Bereichssprache: wer wann welchen Bereich für wen freigegeben oder entzogen hat. Tool-Namen nur in der Expertenansicht. */
export function AreaAuditLog({ lang, expert = false }: { lang: "de" | "en"; expert?: boolean }) {
  const { t } = useTranslation("agents")
  const [rows, setRows] = useState<AuditEntry[] | null>(null)
  const [failed, setFailed] = useState(false)
  useEffect(() => {
    let alive = true
    api.get<{ entries: AuditEntry[] }>(`/admin/area-audit?lang=${lang}&limit=100`)
      .then((r) => { if (alive) setRows(r.entries) }).catch(() => { if (alive) setFailed(true) })
    return () => { alive = false }
  }, [lang])
  if (failed) return <AdminFeedback tone="danger">{t("areas.load_failed")}</AdminFeedback>
  if (rows === null) return <AdminFeedback loading>{t("areas.loading")}</AdminFeedback>
  if (rows.length === 0) return <AdminFeedback>{t("areas.audit_empty")}</AdminFeedback>
  return (
    <ul className="space-y-1.5">
      {rows.map((e, i) => (
        <li key={`${e.at}-${i}`} className="rounded-[4px] border border-s-rand bg-s-innen px-3 py-2 text-xs">
          <span className="text-[#9aa7bc]">{e.at.slice(0, 16).replace("T", " ")} · {e.actor || "?"} · </span>
          <span className="font-bold text-[#e8eef8]">{t(`areas.action.${e.action}`, { defaultValue: e.action })}</span>
          <span className="text-[#9aa7bc]"> · {e.target}</span>
          {e.areas.length > 0 && <span className="block text-[#e8eef8]">{e.areas.join(", ")}</span>}
          {expert && e.tools.length > 0 && <span className="block font-mono text-[#9aa7bc]">{e.tools.join(", ")}</span>}
        </li>
      ))}
    </ul>
  )
}
