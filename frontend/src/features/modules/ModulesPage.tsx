import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ArrowUpCircle, Boxes, RefreshCw } from "lucide-react"
import { HelpButton } from "@/i18n/HelpButton"
import type { ModulesIndex } from "./types"
import { listModules } from "./api"
import { UpdateAllButton, UpdateAllResult } from "./UpdateAllPanel"
import { useUpdateAll } from "./useUpdateAll"
import { ModuleCard } from "./ModuleCard"

export function ModulesPage() {
  const { t } = useTranslation("modules")
  const [data, setData] = useState<ModulesIndex>({ modules: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await listModules())
    } catch (e) {
      setError(String(e))
    }
    setLoading(false)
  }, [])

  // load() ist async — setState passiert nach dem await; die Regel über-feuert hier.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load() }, [load])

  const outdated = data.modules.filter((m) => m.update_available)
  const installedCount = data.modules.filter((m) => m.installed).length

  // Ein Ablauf für alle: einmal bauen, einmal Neustart (docs/specs/modul-update-alle.md).
  const all = useUpdateAll(outdated.length, load)

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Boxes className="text-violet-400" size={20} />
          <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
          <span className="text-xs text-zinc-500">
            {t("installed_count", { count: installedCount })}
          </span>
          {outdated.length > 0 && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/15 text-amber-300 border border-amber-500/30">
              <ArrowUpCircle size={9} />
              {t("update.count", { count: outdated.length })}
            </span>
          )}
          <HelpButton topic="modules" />
        </div>
        <div className="flex items-center gap-2">
          <UpdateAllButton outdatedCount={outdated.length} state={all} onStart={all.start}
            buttonClass="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 text-xs font-medium transition-colors disabled:opacity-60" />
          <button
            onClick={load}
            disabled={loading || all.running}
            aria-label={t("common:actions.refresh")}
            title={t("common:actions.refresh")}
            className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/[5%] transition-colors disabled:opacity-40">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      <UpdateAllResult state={all} onDismiss={all.dismiss} />
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
          {error}
        </div>
      )}

      {loading && data.modules.length === 0 ? (
        <p className="text-zinc-500 text-sm">{t("loading")}</p>
      ) : data.modules.length === 0 ? (
        <p className="text-zinc-500 text-sm">{t("empty")}</p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3">
          {data.modules.map((mod) => (
            <ModuleCard key={mod.id} mod={mod} onRefresh={load} />
          ))}
        </div>
      )}
    </div>
  )
}
