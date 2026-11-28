import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminFeedback } from "@/features/cockpit/admin/ui"
import { api } from "@/shared/api-client"

interface Approval { category: string; tool: string; approved_by: string; approved_at: string; active: boolean }

/** Vorhandene Kategorie-Bestätigungen (`/api/admin/tool-categories`): Expertenansicht, zugeklappt. Widerruf je Eintrag. */
export function CategoryApprovals() {
  const { t } = useTranslation("agents")
  const [rows, setRows] = useState<Approval[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const load = () => api.get<{ approvals: Approval[] }>("/admin/tool-categories")
    .then((r) => setRows(r.approvals)).catch(() => setError(t("areas.load_failed")))
  useEffect(() => { void load() }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  async function revoke(a: Approval) {
    setError(null)
    try {
      await api.delete(`/admin/tool-categories/${encodeURIComponent(a.category)}/${encodeURIComponent(a.tool)}`)
      await load()
    } catch { setError(t("areas.save_failed")) }   // nie Rohtext des Servers (Review #795)
  }

  return (
    <details className="rounded-[4px] border border-s-rand bg-s-innen px-3 py-2">
      <summary className="cursor-pointer text-sm font-bold text-[#e8eef8]">{t("areas.categories_title")}</summary>
      <p className="mt-2 text-xs text-[#9aa7bc]">{t("areas.categories_hint")}</p>
      {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
      {rows !== null && rows.length === 0 && <p className="mt-2 text-xs text-[#9aa7bc]">{t("areas.categories_none")}</p>}
      <ul className="mt-2 space-y-1">
        {(rows ?? []).map((a) => (
          <li key={`${a.category}/${a.tool}`} className="flex items-center justify-between gap-2 text-xs">
            <span className="font-mono text-[#e8eef8]">{a.category} · {a.tool}{a.active ? "" : ` (${t("areas.inactive")})`}</span>
            <AdminAction onClick={() => void revoke(a)}>{t("areas.revoke")}</AdminAction>
          </li>
        ))}
      </ul>
    </details>
  )
}
