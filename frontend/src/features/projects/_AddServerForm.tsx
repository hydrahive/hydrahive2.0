import { useEffect, useState } from "react"
import { Box, HardDrive, Loader2, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import type { ProjectServer } from "./types"

interface Props {
  projectId: string
  onCancel: () => void
  onAdded: () => Promise<void>
}

export function AddServerForm({ projectId, onCancel, onAdded }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [available, setAvailable] = useState<ProjectServer[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    projectsApi.getAvailableServers(projectId)
      .then(setAvailable)
      .catch((e) => setError(e instanceof Error ? e.message : ""))
      .finally(() => setLoading(false))
  }, [projectId])

  async function assign(s: ProjectServer) {
    setBusyId(`${s.kind}:${s.id}`); setError(null)
    try {
      await projectsApi.assignServer(projectId, s.kind, s.id)
      await onAdded()
    } catch (e) {
      setError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setBusyId(null) }
  }

  return (
    <div className="rounded-lg border border-violet-500/20 bg-violet-500/[3%] p-3 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs text-violet-300 font-medium">{t("servers.add_title")}</p>
        <button onClick={onCancel} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
          <X size={12} />
        </button>
      </div>
      {error && (
        <p className="text-xs text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-2 py-1">{error}</p>
      )}
      {loading ? (
        <div className="flex items-center justify-center py-6">
          <Loader2 size={16} className="animate-spin text-zinc-500" />
        </div>
      ) : available.length === 0 ? (
        <p className="text-xs text-zinc-500 py-3 text-center">{t("servers.none_available")}</p>
      ) : (
        <div className="space-y-1">
          {available.map((s) => {
            const Icon = s.kind === "vm" ? HardDrive : Box
            const id = `${s.kind}:${s.id}`
            return (
              <button key={id} onClick={() => assign(s)} disabled={busyId !== null}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-white/[6%] text-left disabled:opacity-50">
                <Icon size={12} className="text-zinc-500 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-zinc-200 truncate">{s.name}</p>
                  <p className="text-[10px] text-zinc-600 truncate">
                    {s.kind.toUpperCase()} · {s.cpu ?? "?"} CPU · {s.ram_mb ?? "?"} MB · {s.actual_state}
                  </p>
                </div>
                {busyId === id && <Loader2 size={11} className="animate-spin text-violet-400" />}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
