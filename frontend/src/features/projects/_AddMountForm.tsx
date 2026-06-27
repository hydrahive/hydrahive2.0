import { useEffect, useState } from "react"
import type { CSSProperties } from "react"
import { FolderInput, Loader2, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import { rgbFor } from "@/shared/colors"
import { CreateMountForm } from "./_CreateMountForm"
import type { SmbMount } from "./types"

interface Props {
  projectId: string
  onCancel: () => void
  onAssigned: () => Promise<void>
}

export function AddMountForm({ projectId, onCancel, onAssigned }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [available, setAvailable] = useState<SmbMount[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function reloadAvailable() {
    setLoading(true)
    try { setAvailable(await projectsApi.getAvailableMounts(projectId)) }
    catch (e) { setError(e instanceof Error ? e.message : "") }
    finally { setLoading(false) }
  }

  useEffect(() => { reloadAvailable() }, [projectId])

  async function assign(m: SmbMount) {
    setBusyId(m.id); setError(null)
    try {
      await projectsApi.assignMount(projectId, m.id)
      await onAssigned()
    } catch (e) {
      setError(e instanceof Error ? e.message : tCommon("status.error"))
      await reloadAvailable()
    } finally { setBusyId(null) }
  }

  return (
    <div className="box overflow-hidden p-3 space-y-2" style={{ "--c": rgbFor("/projects") } as CSSProperties}>
      <div className="flex items-center justify-between">
        <p className="text-xs text-violet-300 font-medium">{t("mounts.add_title")}</p>
        <button onClick={onCancel} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
          <X size={12} />
        </button>
      </div>
      {error && (
        <p className="text-xs text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-2 py-1">{error}</p>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 size={16} className="animate-spin text-zinc-500" />
        </div>
      ) : available.length === 0 ? (
        <p className="text-xs text-zinc-500 py-2 text-center">{t("mounts.none_available")}</p>
      ) : (
        <div className="space-y-1">
          {available.map((m) => (
            <button key={m.id} onClick={() => assign(m)} disabled={busyId !== null}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-white/[6%] text-left disabled:opacity-50">
              <FolderInput size={12} className="text-zinc-500 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-zinc-200 truncate">{m.name}</p>
                <p className="text-[10px] text-zinc-600 truncate font-mono">
                  //{m.host}/{m.share}{m.subpath ? "/" + m.subpath : ""}
                </p>
              </div>
              {busyId === m.id && <Loader2 size={11} className="animate-spin text-violet-400" />}
            </button>
          ))}
        </div>
      )}

      <CreateMountForm onCreated={async () => { await reloadAvailable() }} />
    </div>
  )
}
