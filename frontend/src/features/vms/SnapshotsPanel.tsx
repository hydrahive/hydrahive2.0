import { useEffect, useState } from "react"
import { Camera, Plus, RotateCcw, Trash2, X } from "lucide-react"
import type { Snapshot, VM } from "./types"
import { vmsApi } from "./api"
import { formatBytes, formatRelative } from "./format"

interface Props {
  vm: VM
  onClose: () => void
}

export function SnapshotsPanel({ vm, onClose }: Props) {
  const [snaps, setSnaps] = useState<Snapshot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [busy, setBusy] = useState(false)

  async function refresh() {
    try {
      setError(null)
      setSnaps(await vmsApi.listSnapshots(vm.vm_id))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { void refresh() }, [vm.vm_id])

  const canMutate = vm.actual_state === "stopped"

  async function handleCreate() {
    if (!name.trim()) { setError("Name darf nicht leer sein"); return }
    setBusy(true); setError(null)
    try {
      await vmsApi.createSnapshot(vm.vm_id, name.trim(), description.trim() || undefined)
      setName(""); setDescription("")
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function handleRestore(s: Snapshot) {
    if (!confirm(`Snapshot "${s.name}" wiederherstellen? Aktueller Disk-Stand wird verworfen.`)) return
    setBusy(true); setError(null)
    try {
      await vmsApi.restoreSnapshot(vm.vm_id, s.snapshot_id)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  async function handleDelete(s: Snapshot) {
    if (!confirm(`Snapshot "${s.name}" löschen?`)) return
    setBusy(true); setError(null)
    try {
      await vmsApi.deleteSnapshot(vm.vm_id, s.snapshot_id)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-y-0 right-0 z-30 w-full sm:w-[520px] bg-zinc-900 border-l border-white/[8%] shadow-2xl flex flex-col">
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/[6%]">
        <div className="flex items-center gap-2">
          <Camera size={18} className="text-violet-400" />
          <h2 className="text-lg font-bold text-white">Snapshots — {vm.name}</h2>
        </div>
        <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200"><X size={16} /></button>
      </div>

      <div className="px-5 py-4 border-b border-white/[6%] space-y-3">
        {!canMutate && (
          <div className="text-xs text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded-md px-3 py-2">
            VM muss gestoppt sein für Snapshot-Operationen. Aktuell: <strong>{vm.actual_state}</strong>
          </div>
        )}
        <div className="grid grid-cols-3 gap-2">
          <input
            value={name} onChange={(e) => setName(e.target.value)}
            disabled={!canMutate || busy}
            placeholder="Snapshot-Name (z.B. before-update)"
            className="col-span-2 bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-sm text-zinc-200 disabled:opacity-50 focus:border-violet-500/50 outline-none"
          />
          <button onClick={handleCreate} disabled={!canMutate || busy || !name.trim()}
            className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-violet-500/15 hover:bg-violet-500/25 border border-violet-500/30 text-violet-200 text-xs font-medium disabled:opacity-30">
            <Plus size={13} /> Erstellen
          </button>
        </div>
        <input value={description} onChange={(e) => setDescription(e.target.value)}
          disabled={!canMutate || busy}
          placeholder="Beschreibung (optional)"
          className="w-full bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-xs text-zinc-300 disabled:opacity-50 focus:border-violet-500/50 outline-none"
        />
        {error && <div className="text-xs text-rose-300 bg-rose-500/10 border border-rose-500/20 rounded-md px-3 py-2">{error}</div>}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {loading ? (
          <p className="text-sm text-zinc-500 text-center py-6">Lade…</p>
        ) : snaps.length === 0 ? (
          <p className="text-sm text-zinc-500 text-center py-12">Noch keine Snapshots.</p>
        ) : snaps.map((s) => (
          <div key={s.snapshot_id} className="rounded-lg border border-white/[8%] bg-white/[2%] p-3 space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-mono text-zinc-100 truncate">{s.name}</p>
                {s.description && <p className="text-xs text-zinc-500 mt-0.5">{s.description}</p>}
              </div>
              <div className="text-right flex-shrink-0">
                <p className="text-[11px] text-zinc-400">{formatRelative(s.created_at)}</p>
                {s.size_bytes != null && <p className="text-[11px] text-zinc-500 font-mono">{formatBytes(s.size_bytes)}</p>}
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => handleRestore(s)} disabled={!canMutate || busy}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-200 disabled:opacity-30">
                <RotateCcw size={11} /> Wiederherstellen
              </button>
              <div className="flex-1" />
              <button onClick={() => handleDelete(s)} disabled={!canMutate || busy}
                className="p-1.5 rounded text-zinc-500 hover:text-rose-300 hover:bg-rose-500/10 disabled:opacity-30" title="Löschen">
                <Trash2 size={12} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
