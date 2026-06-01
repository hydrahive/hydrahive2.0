import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Link2, Plus, Trash2 } from "lucide-react"
import { clientsApi } from "./api"
import type { ClientConnection } from "./types"
import { NewClientDialog } from "./_NewClientDialog"

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" })
  } catch {
    return iso
  }
}

export function ClientConnectionsSection() {
  const { t } = useTranslation("federation")
  const [clients, setClients] = useState<ClientConnection[]>([])
  const [loading, setLoading] = useState(true)
  const [showNew, setShowNew] = useState(false)

  async function load() {
    try {
      const data = await clientsApi.list()
      setClients(data)
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleDelete(id: string, name: string) {
    if (!confirm(t("clients.delete_confirm", { name }))) return
    await clientsApi.delete(id).catch(() => {})
    load()
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Link2 size={15} className="text-violet-400" />
          <span className="text-sm font-medium text-zinc-200">{t("clients.title")}</span>
          <span className="text-xs text-zinc-600 ml-1">{t("clients.subtitle")}</span>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-zinc-100 border border-white/[6%] transition-colors"
        >
          <Plus size={12} />
          {t("clients.add")}
        </button>
      </div>

      {loading ? (
        <div className="text-xs text-zinc-600 py-4 text-center">{t("clients.loading")}</div>
      ) : clients.length === 0 ? (
        <div className="rounded-xl border border-white/[4%] bg-zinc-950/30 py-8 text-center">
          <Link2 size={24} className="text-zinc-700 mx-auto mb-2" />
          <p className="text-xs text-zinc-600">{t("clients.empty")}</p>
          <button
            onClick={() => setShowNew(true)}
            className="mt-2 text-xs text-violet-400 hover:text-violet-300 transition-colors"
          >
            {t("clients.add_first")}
          </button>
        </div>
      ) : (
        <div className="space-y-1">
          {clients.map(c => (
            <div
              key={c.id}
              className="flex items-center justify-between rounded-lg border border-white/[5%] bg-zinc-900/60 px-3 py-2.5"
            >
              <div className="flex items-center gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/70" />
                <div>
                  <span className="text-sm text-zinc-200">{c.name}</span>
                  <span className="ml-2 text-xs text-zinc-600">·  {formatDate(c.created_at)}</span>
                </div>
              </div>
              <button
                onClick={() => handleDelete(c.id, c.name)}
                className="p-1 text-zinc-600 hover:text-red-400 transition-colors"
                title={t("clients.remove_title")}
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      )}

      {showNew && (
        <NewClientDialog
          onClose={() => setShowNew(false)}
          onCreated={() => { load() }}
        />
      )}
    </div>
  )
}
