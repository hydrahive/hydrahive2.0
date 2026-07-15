import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { ArrowUpCircle, RefreshCw } from "lucide-react"
import { listModules, updateModule } from "@/features/modules/api"
import type { ModulesIndex } from "@/features/modules/types"
import { CockpitButton } from "../CockpitButton"
import { AdminOverlay } from "./AdminOverlay"
import { ModuleCockpitCard } from "./ModuleCockpitCard"

export function ModulesOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("modules")
  const [data, setData] = useState<ModulesIndex>({ modules: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [batch, setBatch] = useState<{ done: number; total: number } | null>(null)
  const stopRef = useRef<(() => void) | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setData(await listModules()) } catch (e) { setError(String(e)) }
    setLoading(false)
  }, [])

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load() }, [load])
  useEffect(() => () => stopRef.current?.(), [])

  const outdated = data.modules.filter((m) => m.update_available)
  const installedCount = data.modules.filter((m) => m.installed).length

  const updateAll = useCallback(async () => {
    if (outdated.length === 0 || batch) return
    setBatch({ done: 0, total: outdated.length })
    for (let i = 0; i < outdated.length; i++) {
      await new Promise<void>((resolve) => {
        stopRef.current = updateModule(outdated[i].id, () => {}, () => resolve(), () => resolve())
      })
      setBatch({ done: i + 1, total: outdated.length })
    }
    stopRef.current = null
    setBatch(null)
    await load()
  }, [outdated, batch, load])

  return (
    <AdminOverlay
      eyebrow="Admin"
      title={t("title")}
      onClose={onClose}
      maxWidthClass="max-w-5xl"
      headerActions={
        <div className="flex items-center gap-2">
          {outdated.length > 0 && (
            <CockpitButton onClick={updateAll} disabled={batch !== null}>
              <RefreshCw size={12} className={`mr-1 inline ${batch ? "animate-spin" : ""}`} />
              {batch ? t("update.all_running", { done: batch.done, total: batch.total }) : t("update.all")}
            </CockpitButton>
          )}
          <CockpitButton onClick={load} disabled={loading || batch !== null}>
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          </CockpitButton>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-3 text-sm text-[#8d9ab0]">
          <span>{t("installed_count", { count: installedCount })}</span>
          {outdated.length > 0 && (
            <span className="flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-300">
              <ArrowUpCircle size={9} />{t("update.count", { count: outdated.length })}
            </span>
          )}
        </div>

        {error && <div className="rounded-[6px] border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-400">{error}</div>}

        {loading && data.modules.length === 0 ? (
          <p className="text-sm text-[#8d9ab0]">{t("loading")}</p>
        ) : data.modules.length === 0 ? (
          <p className="text-sm text-[#8d9ab0]">{t("empty")}</p>
        ) : (
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {data.modules.map((mod) => <ModuleCockpitCard key={mod.id} mod={mod} onRefresh={load} />)}
          </div>
        )}
      </div>
    </AdminOverlay>
  )
}
