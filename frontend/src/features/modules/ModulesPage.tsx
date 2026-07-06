import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { ArrowUpCircle, Boxes, RefreshCw } from "lucide-react"
import { HelpButton } from "@/i18n/HelpButton"
import type { ModulesIndex } from "./types"
import { listModules, updateModule } from "./api"
import { ModuleCard } from "./ModuleCard"

export function ModulesPage() {
  const { t } = useTranslation("modules")
  const [data, setData] = useState<ModulesIndex>({ modules: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [batch, setBatch] = useState<{ done: number; total: number } | null>(null)
  const stopRef = useRef<(() => void) | null>(null)

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

  useEffect(() => () => stopRef.current?.(), [])

  const outdated = data.modules.filter((m) => m.update_available)
  const installedCount = data.modules.filter((m) => m.installed).length

  /** Alle veralteten Module sequentiell aktualisieren (ein Stream nach dem anderen). */
  const updateAll = useCallback(async () => {
    if (outdated.length === 0 || batch) return
    setBatch({ done: 0, total: outdated.length })
    for (let i = 0; i < outdated.length; i++) {
      await new Promise<void>((resolve) => {
        stopRef.current = updateModule(
          outdated[i].id,
          () => { /* Batch kompakt — pro-Modul-Logs zeigt die Karte selbst */ },
          () => resolve(),
          () => resolve(), // Fehler eines Moduls stoppt den Batch nicht
        )
      })
      setBatch({ done: i + 1, total: outdated.length })
    }
    stopRef.current = null
    setBatch(null)
    await load()
  }, [outdated, batch, load])

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
          <HelpButton topic="modules" prominent />
        </div>
        <div className="flex items-center gap-2">
          {outdated.length > 0 && (
            <button
              onClick={updateAll}
              disabled={batch !== null}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 text-xs font-medium transition-colors disabled:opacity-60">
              <RefreshCw size={12} className={batch ? "animate-spin" : ""} />
              {batch
                ? t("update.all_running", { done: batch.done, total: batch.total })
                : t("update.all")}
            </button>
          )}
          <button
            onClick={load}
            disabled={loading || batch !== null}
            className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/[5%] transition-colors disabled:opacity-40">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

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
