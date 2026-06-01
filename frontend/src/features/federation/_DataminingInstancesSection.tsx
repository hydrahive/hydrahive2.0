import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Copy, Pickaxe, Plus, RefreshCw, Trash2 } from "lucide-react"
import { externalInstancesApi } from "./api"
import type { ExternalInstance } from "./types"
import { NewInstanceDialog } from "./_NewInstanceDialog"

function formatDate(iso: string | null) {
  if (!iso) return "—"
  try {
    return new Date(iso).toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" })
  } catch {
    return iso
  }
}

export function DataminingInstancesSection() {
  const { t } = useTranslation("federation")
  const [instances, setInstances] = useState<ExternalInstance[]>([])
  const [loading, setLoading] = useState(true)
  const [showNew, setShowNew] = useState(false)

  async function load() {
    try {
      setInstances(await externalInstancesApi.list())
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleDelete(inst: ExternalInstance) {
    if (!confirm(t("instances.delete_confirm", { name: inst.name }))) return
    await externalInstancesApi.delete(inst.agent_id).catch(() => {})
    load()
  }

  async function handleRotate(inst: ExternalInstance) {
    if (!confirm(t("instances.rotate_confirm", { name: inst.name }))) return
    try {
      const { api_key } = await externalInstancesApi.rotateKey(inst.agent_id)
      window.prompt(t("instances.new_key_prompt"), api_key)
    } catch { /* ignore */ }
    load()
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Pickaxe size={15} className="text-violet-400" />
          <span className="text-sm font-medium text-zinc-200">{t("instances.title")}</span>
          <span className="text-xs text-zinc-600 ml-1">{t("instances.subtitle")}</span>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-zinc-100 border border-white/[6%] transition-colors"
        >
          <Plus size={12} />
          {t("instances.add")}
        </button>
      </div>

      {loading ? (
        <div className="text-xs text-zinc-600 py-4 text-center">{t("instances.loading")}</div>
      ) : instances.length === 0 ? (
        <div className="rounded-xl border border-white/[4%] bg-zinc-950/30 py-8 text-center">
          <Pickaxe size={24} className="text-zinc-700 mx-auto mb-2" />
          <p className="text-xs text-zinc-600">{t("instances.empty")}</p>
        </div>
      ) : (
        <div className="space-y-1">
          {instances.map(inst => (
            <div key={inst.agent_id}
                 className="flex items-center justify-between rounded-lg border border-white/[5%] bg-zinc-900/60 px-3 py-2.5">
              <div className="flex items-center gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/70" />
                <div>
                  <span className="text-sm text-zinc-200">{inst.name}</span>
                  <span className="ml-2 text-xs text-zinc-600">
                    · {inst.session_count} {t("instances.sessions")} · {t("instances.last_activity")} {formatDate(inst.last_activity)}
                  </span>
                  <div className="mt-0.5 flex items-center gap-1.5 font-mono text-[11px] text-zinc-600">
                    <span className="text-zinc-500">HH_AGENT_ID</span>
                    <span className="text-zinc-400 select-all">{inst.agent_id}</span>
                    <button
                      onClick={() => navigator.clipboard.writeText(inst.agent_id)}
                      className="text-zinc-600 hover:text-violet-400 transition-colors"
                      title={t("instances.copy_agent_id")}
                    >
                      <Copy size={11} />
                    </button>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button onClick={() => handleRotate(inst)}
                        className="p-1 text-zinc-600 hover:text-violet-400 transition-colors" title={t("instances.rotate_key")}>
                  <RefreshCw size={13} />
                </button>
                <button onClick={() => handleDelete(inst)}
                        className="p-1 text-zinc-600 hover:text-red-400 transition-colors" title={t("instances.delete")}>
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showNew && (
        <NewInstanceDialog
          onClose={() => setShowNew(false)}
          onCreated={() => { load() }}
        />
      )}
    </div>
  )
}
