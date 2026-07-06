import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { ArrowUpCircle, Boxes, ChevronDown, ChevronRight, RefreshCw } from "lucide-react"
import type { ModulesIndex } from "./types"
import { listModules, updateModule } from "./api"
import { InstalledModuleCard, AvailableModuleCard } from "./ModuleCard"

export function ModulesPage() {
  const { t } = useTranslation("modules")
  const [data, setData] = useState<ModulesIndex>({ installed: [], available: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [collapsed, setCollapsed] = useState(false)
  const [batch, setBatch] = useState<{ done: number; total: number } | null>(null)
  const stopRef = useRef<(() => void) | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const idx = await listModules()
      setData(idx)
      // Bei vielen installierten Modulen die Sektion einklappen → Übersicht.
      setCollapsed(idx.installed.length > 4)
    } catch (e) {
      setError(String(e))
    }
    setLoading(false)
  }, [])

  // load() ist async — setState passiert nach dem await; die Regel über-feuert hier.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load() }, [load])

  // Laufenden Batch beim Unmount abbrechen.
  useEffect(() => () => stopRef.current?.(), [])

  const outdated = data.installed.filter((m) => m.update_available)

  /** Alle veralteten Module sequentiell aktualisieren (ein Stream nach dem anderen). */
  const updateAll = useCallback(async () => {
    if (outdated.length === 0 || batch) return
    setBatch({ done: 0, total: outdated.length })
    for (let i = 0; i < outdated.length; i++) {
      await new Promise<void>((resolve) => {
        stopRef.current = updateModule(
          outdated[i].id,
          () => { /* Logs pro Modul zeigt die Karte selbst nicht — Batch ist kompakt */ },
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Boxes className="text-violet-400" size={20} />
          <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
          <span className="text-xs text-zinc-500">
            {t("installed_count", { count: data.installed.length })}
          </span>
        </div>
        <button
          onClick={load}
          disabled={loading || batch !== null}
          className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/[5%] transition-colors disabled:opacity-40">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
          {error}
        </div>
      )}

      {/* Installed */}
      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <button
            onClick={() => setCollapsed((v) => !v)}
            className="flex items-center gap-1.5 text-sm font-semibold text-zinc-400 uppercase tracking-wide hover:text-zinc-200 transition-colors">
            {collapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
            {t("section.installed")}
            {outdated.length > 0 && (
              <span className="normal-case tracking-normal flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/15 text-amber-300 border border-amber-500/30">
                <ArrowUpCircle size={9} />
                {t("update.count", { count: outdated.length })}
              </span>
            )}
          </button>
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
        </div>

        {loading && data.installed.length === 0 ? (
          <p className="text-zinc-500 text-sm">{t("loading")}</p>
        ) : data.installed.length === 0 ? (
          <p className="text-zinc-500 text-sm">{t("empty_installed")}</p>
        ) : collapsed ? null : (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3">
            {data.installed.map((mod) => (
              <InstalledModuleCard key={mod.id} mod={mod} onRefresh={load} />
            ))}
          </div>
        )}
      </section>

      {/* Available */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide">
          {t("section.available")}
        </h2>
        {loading && data.available.length === 0 ? (
          <p className="text-zinc-500 text-sm">{t("loading")}</p>
        ) : data.available.length === 0 ? (
          <p className="text-zinc-500 text-sm">{t("empty_available")}</p>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3">
            {data.available.map((mod) => (
              <AvailableModuleCard key={mod.id} mod={mod} onRefresh={load} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
