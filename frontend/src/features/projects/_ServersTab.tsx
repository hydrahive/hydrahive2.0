import { useEffect, useState } from "react"
import {
  Box, ExternalLink, HardDrive, Loader2, Plus, Trash2, X,
} from "lucide-react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
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

function ServerRow({ server, busy, onUnassign }: {
  server: ProjectServer; busy: boolean; onUnassign: () => void
}) {
  const { t } = useTranslation("projects")
  const Icon = server.kind === "vm" ? HardDrive : Box
  const tone = server.actual_state === "running" ? "emerald" :
               server.actual_state === "error" ? "rose" : "zinc"
  const tonePill: Record<string, string> = {
    emerald: "bg-emerald-500/[8%] border-emerald-500/20 text-emerald-300",
    rose: "bg-rose-500/[8%] border-rose-500/20 text-rose-300",
    zinc: "bg-zinc-500/[8%] border-zinc-500/20 text-zinc-400",
  }
  const detailHref = server.kind === "vm" ? `/vms/${server.id}` : `/containers/${server.id}`
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-white/[8%] bg-white/[2%]">
      <Icon size={14} className="text-violet-300 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-zinc-200 truncate">{server.name}</p>
        <p className="text-[10px] text-zinc-600 truncate">
          {server.kind.toUpperCase()} · {server.cpu ?? "?"} CPU · {server.ram_mb ?? "?"} MB
          {server.kind === "vm" && server.disk_gb && ` · ${server.disk_gb} GB`}
          {server.kind === "container" && server.image && ` · ${server.image}`}
        </p>
      </div>
      <span className={`px-2 py-0.5 rounded-full border text-[10px] ${tonePill[tone]}`}>
        {server.actual_state}
      </span>
      <Link to={detailHref}
        className="p-1.5 rounded text-zinc-500 hover:text-violet-300 hover:bg-violet-500/10"
        title={t("servers.open_detail")}>
        <ExternalLink size={12} />
      </Link>
      <button onClick={onUnassign} disabled={busy}
        className="p-1.5 rounded text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 disabled:opacity-30"
        title={t("servers.unassign")}>
        {busy ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
      </button>
    </div>
  )
}

function AddServerForm({ projectId, onCancel, onAdded }: {
  projectId: string; onCancel: () => void; onAdded: () => Promise<void>
}) {
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
