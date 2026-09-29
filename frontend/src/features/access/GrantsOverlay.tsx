import { useCallback, useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { HelpButton } from "@/i18n/HelpButton"
import { AdminOverlay } from "@/features/cockpit/admin/AdminOverlay"
import { AdminFeedback, AdminStatus } from "@/features/cockpit/admin/ui"
import { accessApi } from "./api"
import { adminNames, cellLevel, groupCapabilities, nextLevel, subjectsFor, type MatrixSubject } from "./grantMatrix"
import type { AccessCatalog, CatalogCapability } from "./types"

const cellTone = {
  none: "border-[#2a364b] text-[#5b6675]",
  use: "border-[#69d7ff]/50 bg-[#69d7ff]/10 text-[#69d7ff]",
  manage: "border-emerald-400/50 bg-emerald-400/10 text-emerald-300",
}

export function GrantsOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("access")
  const { t: tCommon } = useTranslation("common")
  const [catalog, setCatalog] = useState<AccessCatalog | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  const load = useCallback(async () => {
    try { setCatalog(await accessApi.catalog()); setError(null) }
    catch (e) { setError(e instanceof Error ? e.message : tCommon("status.error")) }
  }, [tCommon])

  useEffect(() => { const id = window.setTimeout(load, 0); return () => window.clearTimeout(id) }, [load])

  const subjects = useMemo(() => (catalog ? subjectsFor(catalog) : []), [catalog])

  async function toggle(cap: CatalogCapability, s: MatrixSubject) {
    const key = `${cap.id}|${s.key}`
    setBusy(key)
    try {
      const next = nextLevel(cellLevel(cap, s.type, s.id))
      if (next) await accessApi.grant(cap.id, s.type, s.id, next)
      else await accessApi.revoke(cap.id, s.type, s.id)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally {
      setBusy(null)
    }
  }

  return (
    <AdminOverlay eyebrow="Admin" title={t("grants.title")} onClose={onClose} maxWidthClass="max-w-6xl"
      headerActions={<HelpButton topic="access" />}>
      <div className="space-y-4">
        <p className="text-sm text-[#8d9ab0]">{t("grants.description")}</p>
        {catalog && adminNames(catalog).length > 0 && (
          <p className="text-xs text-[#8d9ab0]">{t("grants.admins_always", { names: adminNames(catalog).join(", ") })}</p>
        )}
        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
        {!catalog && !error && <AdminFeedback loading>{t("grants.loading")}</AdminFeedback>}
        {catalog && catalog.capabilities.length === 0 && <AdminFeedback>{t("grants.empty")}</AdminFeedback>}
        {catalog && catalog.capabilities.length > 0 && (
          <div className="overflow-x-auto rounded-[6px] border border-[#2a364b]">
            <table className="w-full text-xs">
              <thead className="bg-[#131b2a] text-[#8d9ab0]">
                <tr>
                  <th className="px-3 py-2 text-left font-bold"> </th>
                  {subjects.map((s) => (
                    <th key={s.key} className="px-2 py-2 text-center font-bold">
                      {s.type === "everyone" ? t("grants.everyone") : s.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {groupCapabilities(catalog.capabilities).map((grp) => [
                  <tr key={`h-${grp.module_id}`} className="bg-[#0d1420]">
                    <td colSpan={subjects.length + 1} className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.12em] text-[#69d7ff]">
                      {grp.module_id || t("grants.core")}
                    </td>
                  </tr>,
                  ...grp.items.map((cap) => (
                    <tr key={cap.id} className="border-t border-[#2a364b]">
                      <td className="px-3 py-2">
                        <p className="font-bold text-[#e8eef8]">{cap.label}</p>
                        <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[10px] text-[#5b6675]">
                          <code>{cap.id}</code>
                          {cap.default === "admin_only" && <AdminStatus>{t("grants.default_admin_only")}</AdminStatus>}
                          {cap.tools.length > 0 && <span>{t("grants.tools", { tools: cap.tools.join(", ") })}</span>}
                        </p>
                      </td>
                      {subjects.map((s) => {
                        const lvl = cellLevel(cap, s.type, s.id)
                        return (
                          <td key={s.key} className="px-2 py-2 text-center">
                            <button type="button" disabled={busy !== null} onClick={() => toggle(cap, s)}
                              className={`min-w-[74px] rounded-[4px] border px-2 py-1 ${cellTone[lvl ?? "none"]} disabled:opacity-50`}>
                              {lvl ? t(`grants.level_${lvl}`) : t("grants.level_none")}
                            </button>
                          </td>
                        )
                      })}
                    </tr>
                  )),
                ])}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AdminOverlay>
  )
}
