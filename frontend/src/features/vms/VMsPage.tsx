import { useTranslation } from "react-i18next"
import { useCallback, useEffect, useMemo, useState } from "react"
import type { CSSProperties } from "react"
import { Disc, Download, Plus, RefreshCw } from "lucide-react"
import { rgbFor } from "@/shared/colors"
import type { VM } from "./types"
import { vmsApi } from "./api"
import { VMCard } from "./VMCard"
import { CreateVMDialog } from "./CreateVMDialog"
import { EditVMDialog } from "./EditVMDialog"
import { ISOLibraryPanel } from "./ISOLibraryPanel"
import { VMConsoleModal } from "./VMConsoleModal"
import { SnapshotsPanel } from "./SnapshotsPanel"
import { ImportJobsPanel } from "./ImportJobsPanel"
import { VMLogsPanel } from "./VMLogsPanel"

const POLL_MS = 4000

export function VMsPage() {
  const { t } = useTranslation("vms")
  const [vms, setVms] = useState<VM[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [showISOs, setShowISOs] = useState(false)
  const [consoleVm, setConsoleVm] = useState<VM | null>(null)
  const [snapshotVm, setSnapshotVm] = useState<VM | null>(null)
  const [showImports, setShowImports] = useState(false)
  const [logsVm, setLogsVm] = useState<VM | null>(null)
  const [editVm, setEditVm] = useState<VM | null>(null)

  const refresh = useCallback(async () => {
    try {
      setError(null)
      setVms(await vmsApi.list())
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
    const running = vms.filter((v) => v.actual_state === "running")
    const cpu = running.reduce((s, v) => s + v.cpu, 0)
    const ram = running.reduce((s, v) => s + v.ram_mb, 0)
    const disk = vms.reduce((s, v) => s + v.disk_gb, 0)
    return { total: vms.length, running: running.length, cpu, ramGb: ram / 1024, diskGb: disk }
  }, [vms])

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">{t("title")}</h1>
          <p className="text-zinc-500 text-sm mt-0.5">{t("subtitle")}</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowImports(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-300 text-xs font-medium hover:bg-white/[8%]">
            <Download size={12} /> {t("imports.button")}
          </button>
          <button onClick={() => setShowISOs(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-300 text-xs font-medium hover:bg-white/[8%]">
            <Disc size={12} /> {t("iso.title")}
          </button>
          <button onClick={refresh}
            className="p-2 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-400 hover:text-zinc-200" title={t("refresh")}>
            <RefreshCw size={13} />
          </button>
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 text-white text-xs font-medium hover:from-indigo-500 hover:to-violet-500 shadow-md shadow-violet-900/20">
            <Plus size={13} /> {t("new_vm")}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <SummaryCard label={t("summary.total")} value={summary.total} />
        <SummaryCard label={t("summary.running")} value={summary.running} highlight />
        <SummaryCard label={t("summary.vcpu")} value={summary.cpu} />
        <SummaryCard label={t("summary.ram")} value={`${summary.ramGb.toFixed(1)} GB`} />
      </div>

      {error && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>
      )}

      {loading ? (
        <p className="text-sm text-zinc-500">{t("loading")}</p>
      ) : vms.length === 0 ? (
        <div className="box overflow-hidden p-10 text-center" style={{ "--c": rgbFor("/vms") } as CSSProperties}>
          <p className="text-sm text-zinc-400">{t("empty")} <span className="text-violet-300">{t("empty_cta")}</span> {t("empty_suffix")}</p>
          <p className="text-xs text-zinc-600 mt-2">{t("tip")} {t("tip_iso")}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {vms.map((vm) => (
            <VMCard key={vm.vm_id} vm={vm}
              onStart={async () => { await vmsApi.start(vm.vm_id); await refresh() }}
              onStop={async () => { await vmsApi.stop(vm.vm_id); await refresh() }}
              onPoweroff={async () => { await vmsApi.poweroff(vm.vm_id); await refresh() }}
              onDelete={async () => { await vmsApi.remove(vm.vm_id); await refresh() }}
              onConsole={() => setConsoleVm(vm)}
              onSnapshots={() => setSnapshotVm(vm)}
              onLogs={() => setLogsVm(vm)}
              onEdit={() => setEditVm(vm)}
            />
          ))}
        </div>
      )}

      {showCreate && <CreateVMDialog onClose={() => setShowCreate(false)} onCreated={refresh} />}
      {editVm && (
        <EditVMDialog vm={editVm}
          onClose={() => setEditVm(null)}
          onSaved={async () => { setEditVm(null); await refresh() }} />
      )}
      {showISOs && <ISOLibraryPanel onClose={() => setShowISOs(false)} />}
      {consoleVm && <VMConsoleModal vm={consoleVm} onClose={() => setConsoleVm(null)} />}
      {snapshotVm && <SnapshotsPanel vm={snapshotVm} onClose={() => setSnapshotVm(null)} />}
      {showImports && <ImportJobsPanel onClose={() => setShowImports(false)} />}
      {logsVm && <VMLogsPanel vm={logsVm} onClose={() => setLogsVm(null)} />}
    </div>
  )
}

function SummaryCard({ label, value, highlight }: { label: string; value: number | string; highlight?: boolean }) {
  return (
    <div className={`box overflow-hidden p-4 ${highlight ? "border-emerald-500/30 bg-emerald-500/5" : ""}`} style={{ "--c": rgbFor("/vms") } as CSSProperties}>
      <p className="text-[11px] uppercase tracking-wider text-zinc-500">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${highlight ? "text-emerald-200" : "text-zinc-100"}`}>{value}</p>
    </div>
  )
}
