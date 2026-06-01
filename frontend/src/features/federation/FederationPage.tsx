import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Globe, Plus } from "lucide-react"
import { federationApi } from "./api"
import type { Workstation } from "./types"
import { WorkstationCard } from "./_WorkstationCard"
import { AddWorkstationDialog } from "./_AddDialog"
import { ClientConnectionsSection } from "./_ClientConnectionsSection"
import { DataminingInstancesSection } from "./_DataminingInstancesSection"

export function FederationPage() {
  const { t } = useTranslation("federation")
  const [workstations, setWorkstations] = useState<Workstation[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)

  async function load() {
    try {
      const data = await federationApi.list()
      setWorkstations(data)
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleDelete(id: string) {
    if (!confirm(t("delete_confirm"))) return
    await federationApi.delete(id).catch(() => {})
    load()
  }

  async function handleToggle(id: string, enabled: boolean) {
    await federationApi.update(id, { enabled }).catch(() => {})
    load()
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Globe className="text-violet-400" size={20} />
          <div>
            <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
            <p className="text-xs text-zinc-500 mt-0.5">{t("subtitle")}</p>
          </div>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm bg-violet-600 hover:bg-violet-500 text-white transition-colors"
        >
          <Plus size={14} />
          {t("add")}
        </button>
      </div>

      <div className="rounded-xl border border-white/[6%] bg-zinc-950/50 p-4 space-y-2">
        <p className="text-xs text-zinc-500">
          Registrierte Workstations sind über <code className="text-violet-400">ask_agent("persona@name", …)</code> erreichbar.
          Der Token ist das <code className="text-zinc-400">PROJEKTX_REMOTE_TOKEN</code> der Ziel-Workstation.
        </p>
      </div>

      {loading ? (
        <div className="text-sm text-zinc-600 py-8 text-center">{t("loading")}</div>
      ) : workstations.length === 0 ? (
        <div className="rounded-xl border border-white/[4%] bg-zinc-950/30 py-12 text-center">
          <Globe size={32} className="text-zinc-700 mx-auto mb-3" />
          <p className="text-sm text-zinc-600">{t("empty")}</p>
          <button
            onClick={() => setShowAdd(true)}
            className="mt-3 text-xs text-violet-400 hover:text-violet-300 transition-colors"
          >
            {t("add_first")}
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {workstations.map(ws => (
            <WorkstationCard
              key={ws.id}
              ws={ws}
              onRefresh={load}
              onDelete={handleDelete}
              onToggle={handleToggle}
            />
          ))}
        </div>
      )}

      {showAdd && (
        <AddWorkstationDialog
          onClose={() => setShowAdd(false)}
          onCreated={() => { setShowAdd(false); load() }}
        />
      )}

      <div className="border-t border-white/[4%] pt-4">
        <ClientConnectionsSection />
      </div>

      <div className="border-t border-white/[4%] pt-4">
        <DataminingInstancesSection />
      </div>
    </div>
  )
}
