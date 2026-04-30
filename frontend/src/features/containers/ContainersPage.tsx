import { useCallback, useEffect, useMemo, useState } from "react"
import { Box, Plus, RefreshCw } from "lucide-react"
import type { Container } from "./types"
import { containersApi } from "./api"
import { ContainerCard } from "./ContainerCard"
import { CreateContainerDialog } from "./CreateContainerDialog"

const POLL_MS = 4000

export function ContainersPage() {
  const [containers, setContainers] = useState<Container[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  const refresh = useCallback(async () => {
    try {
      setError(null)
      setContainers(await containersApi.list())
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
    const t = setInterval(refresh, POLL_MS)
    return () => clearInterval(t)
  }, [refresh])

  const summary = useMemo(() => {
    const running = containers.filter((c) => c.actual_state === "running")
    return { total: containers.length, running: running.length }
  }, [containers])

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">Container</h1>
          <p className="text-zinc-500 text-sm mt-0.5">LXC via incus — leichtgewichtige Dienste in br0, ohne VM-Overhead.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={refresh}
            className="p-2 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-400 hover:text-zinc-200" title="Aktualisieren">
            <RefreshCw size={13} />
          </button>
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 text-white text-xs font-medium hover:from-indigo-500 hover:to-violet-500 shadow-md shadow-violet-900/20">
            <Plus size={13} /> Neuer Container
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <SummaryCard label="Container gesamt" value={summary.total} />
        <SummaryCard label="Laufend" value={summary.running} highlight />
      </div>

      {error && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>
      )}

      {loading ? (
        <p className="text-sm text-zinc-500">Lade…</p>
      ) : containers.length === 0 ? (
        <div className="rounded-xl border border-dashed border-white/[10%] bg-white/[2%] p-10 text-center">
          <Box size={28} className="mx-auto text-zinc-600 mb-3" />
          <p className="text-sm text-zinc-400">Noch keine Container.</p>
          <p className="text-xs text-zinc-600 mt-2">Tipp: <span className="text-violet-300">debian/12</span> ist gut für die meisten Dienste, <span className="text-violet-300">alpine/3.21</span> für Minimum-Footprint.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {containers.map((c) => (
            <ContainerCard key={c.container_id} container={c}
              onStart={async () => { await containersApi.start(c.container_id); await refresh() }}
              onStop={async () => { await containersApi.stop(c.container_id); await refresh() }}
              onRestart={async () => { await containersApi.restart(c.container_id); await refresh() }}
              onDelete={async () => { await containersApi.remove(c.container_id); await refresh() }}
            />
          ))}
        </div>
      )}

      {showCreate && <CreateContainerDialog onClose={() => setShowCreate(false)} onCreated={refresh} />}
    </div>
  )
}

function SummaryCard({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className={`rounded-xl border p-4 ${highlight ? "border-emerald-500/30 bg-emerald-500/5" : "border-white/[8%] bg-white/[2%]"}`}>
      <p className="text-[11px] uppercase tracking-wider text-zinc-500">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${highlight ? "text-emerald-200" : "text-zinc-100"}`}>{value}</p>
    </div>
  )
}
