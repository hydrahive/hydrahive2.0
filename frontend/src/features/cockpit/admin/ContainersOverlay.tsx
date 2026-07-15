import { useCallback, useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { Box, Plus, RefreshCw } from "lucide-react"
import type { Container } from "@/features/containers/types"
import { containersApi } from "@/features/containers/api"
import { ContainerCard } from "@/features/containers/ContainerCard"
import { CreateContainerDialog } from "@/features/containers/CreateContainerDialog"
import { EditContainerDialog } from "@/features/containers/EditContainerDialog"
import { CockpitButton } from "../CockpitButton"
import { AdminOverlay } from "./AdminOverlay"

const POLL_MS = 4000

export function ContainersOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("containers")
  const [containers, setContainers] = useState<Container[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [editC, setEditC] = useState<Container | null>(null)

  const refresh = useCallback(async () => {
    try { setError(null); setContainers(await containersApi.list()) }
    catch (e) { setError(e instanceof Error ? e.message : String(e)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => {
    void refresh()
    const id = setInterval(refresh, POLL_MS)
    return () => clearInterval(id)
  }, [refresh])

  const summary = useMemo(() => {
    const running = containers.filter((c) => c.actual_state === "running")
    return { total: containers.length, running: running.length }
  }, [containers])

  return (
    <AdminOverlay
      eyebrow="Admin"
      title={t("title")}
      onClose={onClose}
      maxWidthClass="max-w-6xl"
      headerActions={
        <div className="flex items-center gap-2">
          <CockpitButton onClick={refresh}><RefreshCw size={13} className={loading ? "animate-spin" : ""} /></CockpitButton>
          <CockpitButton tone="primary" onClick={() => setShowCreate(true)}>
            <Plus size={13} className="mr-1 inline" />{t("detail.new")}
          </CockpitButton>
        </div>
      }
    >
      <div className="space-y-6">
        <p className="text-sm text-[#8d9ab0]">{t("detail.subtitle")}</p>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <SummaryCard label={t("summary.total")} value={summary.total} />
          <SummaryCard label={t("summary.running")} value={summary.running} highlight />
        </div>

        {error && <div className="rounded-[6px] border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>}

        {loading ? (
          <p className="text-sm text-[#8d9ab0]">{t("loading")}</p>
        ) : containers.length === 0 ? (
          <div className="rounded-[6px] border border-[#2a364b] bg-[#111827] p-10 text-center">
            <Box size={28} className="mx-auto mb-3 text-[#5b6675]" />
            <p className="text-sm text-[#8d9ab0]">{t("empty")}</p>
            <p className="mt-2 text-xs text-[#5b6675]">{t("logs.tip")} <span className="text-violet-300">debian/12</span> ist gut für die meisten Dienste, <span className="text-violet-300">alpine/3.21</span> für Minimum-Footprint.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {containers.map((c) => (
              <ContainerCard key={c.container_id} container={c}
                onStart={async () => { await containersApi.start(c.container_id); await refresh() }}
                onStop={async () => { await containersApi.stop(c.container_id); await refresh() }}
                onRestart={async () => { await containersApi.restart(c.container_id); await refresh() }}
                onDelete={async () => { await containersApi.remove(c.container_id); await refresh() }}
                onEdit={() => setEditC(c)}
              />
            ))}
          </div>
        )}
      </div>

      {showCreate && <CreateContainerDialog onClose={() => setShowCreate(false)} onCreated={refresh} />}
      {editC && (
        <EditContainerDialog container={editC} onClose={() => setEditC(null)}
          onSaved={async () => { setEditC(null); await refresh() }} />
      )}
    </AdminOverlay>
  )
}

function SummaryCard({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className={`rounded-[6px] border p-4 ${highlight ? "border-emerald-500/30 bg-emerald-500/5" : "border-[#2a364b] bg-[#111827]"}`}>
      <p className="text-[11px] uppercase tracking-wider text-[#8d9ab0]">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${highlight ? "text-emerald-200" : "text-[#e8eef8]"}`}>{value}</p>
    </div>
  )
}
