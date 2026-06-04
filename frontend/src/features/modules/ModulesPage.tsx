import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Boxes, RefreshCw } from "lucide-react"
import type { ModulesIndex } from "./types"
import { listModules } from "./api"
import { InstalledModuleCard, AvailableModuleCard } from "./ModuleCard"

export function ModulesPage() {
  const { t } = useTranslation("modules")
  const [data, setData] = useState<ModulesIndex>({ installed: [], available: [] })
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
          className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/[5%] transition-colors">
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
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wide">
          {t("section.installed")}
        </h2>
        {loading && data.installed.length === 0 ? (
          <p className="text-zinc-500 text-sm">{t("loading")}</p>
        ) : data.installed.length === 0 ? (
          <p className="text-zinc-500 text-sm">{t("empty_installed")}</p>
        ) : (
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
