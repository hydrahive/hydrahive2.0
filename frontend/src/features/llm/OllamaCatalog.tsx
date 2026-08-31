import { ChevronDown, ChevronRight, Cpu, HardDrive, Loader2, RefreshCw, Search } from "lucide-react"
import { useCallback, useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { ollamaCatalogApi, type OllamaCatalog as Catalog, type OllamaModel, type OllamaPullJob } from "./ollamaApi"
import { OllamaModelList } from "./OllamaModelList"

interface Props {
  onUse: (model: string) => void
}

function hardwareValue(system: Record<string, unknown> | null | undefined, key: string): string | null {
  const value = system?.[key]
  return typeof value === "string" || typeof value === "number" ? String(value) : null
}

export function OllamaCatalog({ onUse }: Props) {
  const { t } = useTranslation("llm")
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [expanded, setExpanded] = useState<string | null>(null)
  const [variants, setVariants] = useState<Record<string, OllamaModel[]>>({})
  const [variantLoading, setVariantLoading] = useState<string | null>(null)
  const [jobs, setJobs] = useState<Record<string, OllamaPullJob>>({})
  const [busyModel, setBusyModel] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setCatalog(await ollamaCatalogApi.get())
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setLoading(false)
    }
  }, [])

  // Initiale Synchronisation mit dem serverseitigen Katalog.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void load() }, [load])

  const loadFamily = useCallback(async (family: string, force = false) => {
    if (!force && variants[family]) return
    setVariantLoading(family)
    try {
      const result = await ollamaCatalogApi.family(family)
      setVariants((current) => ({ ...current, [family]: result.models }))
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setVariantLoading(null)
    }
  }, [variants])

  useEffect(() => {
    const active = Object.values(jobs).filter((job) => job.status === "queued" || job.status === "pulling")
    if (!active.length) return
    const timer = window.setInterval(() => {
      void Promise.all(active.map((job) => ollamaCatalogApi.pullStatus(job.id))).then((updates) => {
        let refresh = false
        setJobs((current) => {
          const next = { ...current }
          updates.forEach((job) => {
            next[job.model] = job
            if (job.status === "success") refresh = true
          })
          return next
        })
        if (refresh) {
          void load()
          if (expanded) void loadFamily(expanded, true)
        }
      }).catch(() => undefined)
    }, 1000)
    return () => window.clearInterval(timer)
  }, [jobs, expanded, load, loadFamily])

  const families = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return catalog?.families ?? []
    return (catalog?.families ?? []).filter((family) =>
      family.name.includes(query) || family.description?.toLowerCase().includes(query),
    )
  }, [catalog?.families, search])

  async function toggleFamily(family: string) {
    if (expanded === family) {
      setExpanded(null)
      return
    }
    setExpanded(family)
    await loadFamily(family)
  }

  async function install(model: string) {
    setBusyModel(model)
    try {
      const job = await ollamaCatalogApi.pull(model)
      setJobs((current) => ({ ...current, [model]: job }))
      setError(null)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setBusyModel(null)
    }
  }

  async function remove(model: string) {
    if (!window.confirm(t("ollama.remove_confirm", { model }))) return
    setBusyModel(model)
    try {
      await ollamaCatalogApi.delete(model)
      setJobs((current) => {
        const next = { ...current }
        delete next[model]
        return next
      })
      await load()
      if (expanded) await loadFamily(expanded, true)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught))
    } finally {
      setBusyModel(null)
    }
  }

  if (loading && !catalog) return <div className="flex justify-center py-12"><Loader2 className="animate-spin text-violet-400" /></div>

  const system = catalog?.hardware_fit.system
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <StatusCard icon={<Cpu size={15} />} title={t("ollama.connection")} value={catalog?.connected ? t("ollama.connected") : t("ollama.offline")} ok={catalog?.connected} />
        <StatusCard icon={<HardDrive size={15} />} title={t("ollama.installed_models")} value={String(catalog?.installed_models.length ?? 0)} ok />
        <StatusCard icon={<Cpu size={15} />} title="llmfit" value={catalog?.hardware_fit.available
          ? [hardwareValue(system, "gpu_name"), hardwareValue(system, "gpu_vram_gb") && `${hardwareValue(system, "gpu_vram_gb")} GB`].filter(Boolean).join(" · ") || t("ollama.fit_available")
          : t(`ollama.${catalog?.hardware_fit.reason || "fit_unavailable"}`)} ok={catalog?.hardware_fit.available} />
      </div>

      {error && <p className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">{error}</p>}
      {catalog?.library_error && <p className="text-xs text-amber-400">{t("ollama.library_offline")}</p>}

      {!!catalog?.installed_models.length && (
        <section className="overflow-hidden rounded-xl border border-white/[7%] bg-white/[2%]">
          <h2 className="border-b border-white/[6%] px-4 py-3 text-sm font-medium text-zinc-200">{t("ollama.installed_models")}</h2>
          <OllamaModelList models={catalog.installed_models} jobs={jobs} busyModel={busyModel} onInstall={install} onDelete={remove} onUse={onUse} />
        </section>
      )}

      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t("ollama.search")}
            className="w-full rounded-lg border border-white/[8%] bg-white/[3%] py-2 pl-9 pr-3 text-sm text-zinc-200 outline-none focus:ring-1 focus:ring-violet-500/50" />
        </div>
        <button onClick={() => void load()} disabled={loading} className="rounded-lg p-2 text-zinc-400 hover:bg-white/5 disabled:opacity-50" title={t("ollama.refresh")}>
          <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      <section className="overflow-hidden rounded-xl border border-white/[7%] bg-white/[2%]">
        {families.map((family) => (
          <div key={family.name} className="border-b border-white/[6%] last:border-0">
            <button onClick={() => void toggleFamily(family.name)} className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-white/[2%]">
              {expanded === family.name ? <ChevronDown size={15} className="mt-1 text-zinc-500" /> : <ChevronRight size={15} className="mt-1 text-zinc-500" />}
              <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className="font-mono text-sm text-zinc-100">{family.name}</span>
                {!!family.installed_count && <span className="text-[10px] text-emerald-400">{t("ollama.installed_count", { count: family.installed_count })}</span>}
                {family.capabilities.map((cap) => <span key={cap} className="rounded bg-white/[5%] px-1.5 py-0.5 text-[10px] text-zinc-400">{cap}</span>)}</div>
                <p className="mt-1 line-clamp-2 text-xs text-zinc-500">{family.description}</p></div>
            </button>
            {expanded === family.name && (variantLoading === family.name
              ? <div className="flex justify-center py-5"><Loader2 size={16} className="animate-spin text-violet-400" /></div>
              : <OllamaModelList models={variants[family.name] ?? []} jobs={jobs} busyModel={busyModel} onInstall={install} onDelete={remove} onUse={onUse} />)}
          </div>
        ))}
        {!families.length && <p className="py-8 text-center text-sm text-zinc-600">{t("ollama.no_models")}</p>}
      </section>
    </div>
  )
}

function StatusCard({ icon, title, value, ok }: { icon: React.ReactNode; title: string; value: string; ok?: boolean }) {
  return <div className="rounded-xl border border-white/[7%] bg-white/[2%] p-3"><div className="flex items-center gap-2 text-xs text-zinc-500">{icon}{title}</div>
    <p className={`mt-1 truncate text-sm ${ok ? "text-zinc-200" : "text-amber-300"}`}>{value}</p></div>
}
