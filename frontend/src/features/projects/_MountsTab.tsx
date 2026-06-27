import { useEffect, useState } from "react"
import { Loader2, Plus } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import { MountRow } from "./_MountRow"
import { AddMountForm } from "./_AddMountForm"
import type { SmbMount } from "./types"

interface Props {
  projectId: string
}

export function MountsTab({ projectId }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [mounts, setMounts] = useState<SmbMount[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  async function reload() {
    setLoading(true); setError(null)
    try { setMounts(await projectsApi.getProjectMounts(projectId)) }
    catch (e) {
      setError(e instanceof Error ? e.message : "")
      setMounts([])
    } finally { setLoading(false) }
  }

  useEffect(() => { reload(); setShowAdd(false) }, [projectId])

  async function unassign(m: SmbMount) {
    if (!confirm(t("mounts.unassign_confirm"))) return
    setBusyId(m.id); setError(null)
    try {
      await projectsApi.unassignMount(projectId, m.id)
      await reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setBusyId(null) }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 size={20} className="animate-spin text-zinc-500" />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-zinc-500">
          {mounts.length === 0
            ? t("mounts.empty")
            : t("mounts.count", { count: mounts.length })}
        </p>
        {!showAdd && (
          <button onClick={() => setShowAdd(true)}
            className="flex items-center gap-1 px-3 py-1 rounded-md bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium">
            <Plus size={11} /> {t("mounts.add")}
          </button>
        )}
      </div>

      {error && (
        <p className="text-xs text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-3 py-2">{error}</p>
      )}

      {showAdd && (
        <AddMountForm
          projectId={projectId}
          onCancel={() => setShowAdd(false)}
          onAssigned={async () => { setShowAdd(false); await reload() }}
        />
      )}

      {mounts.map((m) => (
        <MountRow key={m.id} mount={m}
          busy={busyId === m.id}
          onUnassign={() => unassign(m)} />
      ))}
    </div>
  )
}
