import { useEffect, useState } from "react"
import { Loader2, Plus } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import { ServerRow } from "./_ServerRow"
import { AddServerForm } from "./_AddServerForm"
import type { ProjectServer, ServerKind } from "./types"

interface Props {
  projectId: string
}

export function ServersTab({ projectId }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [servers, setServers] = useState<ProjectServer[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  async function reload() {
    setLoading(true); setError(null)
    try { setServers(await projectsApi.getServers(projectId)) }
    catch (e) {
      setError(e instanceof Error ? e.message : "")
      setServers([])
    } finally { setLoading(false) }
  }

  useEffect(() => { reload(); setShowAdd(false) }, [projectId])

  async function unassign(kind: ServerKind, id: string) {
    if (!confirm(t("servers.unassign_confirm"))) return
    setBusyId(`${kind}:${id}`); setError(null)
    try {
      await projectsApi.unassignServer(projectId, kind, id)
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
          {servers.length === 0
            ? t("servers.empty")
            : t("servers.count", { count: servers.length })}
        </p>
        {!showAdd && (
          <button onClick={() => setShowAdd(true)}
            className="flex items-center gap-1 px-3 py-1 rounded-md bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium">
            <Plus size={11} /> {t("servers.add")}
          </button>
        )}
      </div>

      {error && (
        <p className="text-xs text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-3 py-2">{error}</p>
      )}

      {showAdd && (
        <AddServerForm
          projectId={projectId}
          onCancel={() => setShowAdd(false)}
          onAdded={async () => { setShowAdd(false); await reload() }}
        />
      )}

      {servers.map((s) => (
        <ServerRow key={`${s.kind}:${s.id}`} server={s}
          busy={busyId === `${s.kind}:${s.id}`}
          onUnassign={() => unassign(s.kind, s.id)} />
      ))}
    </div>
  )
}
