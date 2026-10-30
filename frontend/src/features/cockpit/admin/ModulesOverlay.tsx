import { useCallback, useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { ArrowUpCircle, RefreshCw, Search } from "lucide-react"
import { listModules } from "@/features/modules/api"
import { UpdateAllButton, UpdateAllResult } from "@/features/modules/UpdateAllPanel"
import { useUpdateAll } from "@/features/modules/useUpdateAll"
import type { ModulesIndex } from "@/features/modules/types"
import { CockpitButton } from "../CockpitButton"
import { AdminOverlay } from "./AdminOverlay"
import { modulesStatus } from "./overlayStatus"
import { ModuleCockpitCard } from "./ModuleCockpitCard"
import { moduleTabs, moduleView, parseModuleTab, type ModuleTab } from "./moduleTabs"
import { AdminFeedback, AdminTabs, adminInputClass } from "./ui"
import { ADMIN_OVERLAY_THEME } from "@/shared/brand/boxThemes"

export function ModulesOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("modules")
  const [data, setData] = useState<ModulesIndex>({ modules: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState("")
  // Module mit einer Aktion in dieser Sitzung bleiben in ihrem Reiter (Protokoll soll nicht verschwinden).
  const [pinned, setPinned] = useState<ReadonlyMap<string, ModuleTab>>(new Map())
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = parseModuleTab(searchParams.get("tab"))
  function selectTab(next: ModuleTab) {
    const params = new URLSearchParams(searchParams)
    params.set("tab", next)
    setSearchParams(params, { replace: true })
  }

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setData(await listModules()) } catch (e) { setError(String(e)) }
    setLoading(false)
  }, [])

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load() }, [load])

  const outdated = data.modules.filter((m) => m.update_available)
  const visible = moduleView(data.modules, tab, query, pinned)
  const installedCount = data.modules.filter((m) => m.installed).length

  // Ein Ablauf für alle: einmal bauen, einmal Neustart (docs/specs/modul-update-alle.md).
  const all = useUpdateAll(outdated.length, load)

  return (
    <AdminOverlay theme={ADMIN_OVERLAY_THEME["modules"]} status={modulesStatus({ error, outdated: outdated.length })}
      eyebrow="Admin"
      title={t("title")}
      onClose={onClose}
      maxWidthClass="max-w-5xl"
      headerActions={
        <div className="flex items-center gap-2">
          <UpdateAllButton outdatedCount={outdated.length} state={all} onStart={all.start}
            buttonClass="flex items-center gap-1.5 rounded-[4px] border border-amber-500/30 bg-amber-500/15 px-3 py-1.5 text-xs font-bold text-amber-200 hover:bg-amber-500/25 disabled:opacity-70" />
          <CockpitButton onClick={load} disabled={loading || all.running}>
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          </CockpitButton>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-3 text-sm text-[#9aa7bc]">
          <span>{t("installed_count", { count: installedCount })}</span>
          {outdated.length > 0 && (
            <span className="flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-300">
              <ArrowUpCircle size={9} />{t("update.count", { count: outdated.length })}
            </span>
          )}
        </div>

        <UpdateAllResult state={all} onDismiss={all.dismiss} />
        {error && <div className="rounded-[6px] border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-400">{error}</div>}

        <label className="relative block">
          <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#9aa7bc]" aria-hidden="true" />
          <span className="sr-only">{t("search.label")}</span>
          <input type="search" value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder={t("search.placeholder")} className={`${adminInputClass} pl-9`} />
        </label>

        <AdminTabs label={t("title")} idPrefix="modules" active={tab} onSelect={selectTab}
          tabs={moduleTabs(data.modules, query, t)}>
          {loading && data.modules.length === 0 ? (
            <AdminFeedback loading>{t("loading")}</AdminFeedback>
          ) : visible.length === 0 ? (
            <AdminFeedback>{query.trim() ? t("search.none") : t("empty")}</AdminFeedback>
          ) : (
            <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
              {visible.map((mod) => (
                <ModuleCockpitCard key={mod.id} mod={mod} onRefresh={load}
                  onAction={() => setPinned((p) => new Map(p).set(mod.id, tab))} />
              ))}
            </div>
          )}
        </AdminTabs>
      </div>
    </AdminOverlay>
  )
}
