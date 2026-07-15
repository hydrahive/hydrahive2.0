import { useCallback, useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { Disc, Download, Plus, RefreshCw } from "lucide-react"
import type { VM } from "@/features/vms/types"
import { vmsApi } from "@/features/vms/api"
import { VMCard } from "@/features/vms/VMCard"
import { CreateVMDialog } from "@/features/vms/CreateVMDialog"
import { EditVMDialog } from "@/features/vms/EditVMDialog"
import { ISOLibraryPanel } from "@/features/vms/ISOLibraryPanel"
import { VMConsoleModal } from "@/features/vms/VMConsoleModal"
import { SnapshotsPanel } from "@/features/vms/SnapshotsPanel"
import { ImportJobsPanel } from "@/features/vms/ImportJobsPanel"
import { VMLogsPanel } from "@/features/vms/VMLogsPanel"
import { CockpitButton } from "../CockpitButton"
import { AdminOverlay } from "./AdminOverlay"

const POLL_MS = 4000

export function VMsOverlay({ onClose }: { onClose: () => void }) {
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
    try { setError(null); setVms(await vmsApi.list()) }
    catch (e) { setError(e instanceof Error ? e.message : String(e)) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => {
    void refresh()
    const id = setInterval(refresh, POLL_MS)
    return () => clearInterval(id)
  }, [refresh])

  const summary = useMemo(() => {
    const running = vms.filter((v) => v.actual_state === "running")
    const cpu = running.reduce((s, v) => s + v.cpu, 0)
    const ram = running.reduce((s, v) => s + v.ram_mb, 0)
    const disk = vms.reduce((s, v) => s + v.disk_gb, 0)
    return { total: vms.length, running: running.length, cpu, ramGb: ram / 1024, diskGb: disk }
  }, [vms])

  return (
    <AdminOverlay
      eyebrow="Admin"
      title={t("title")}
      onClose={onClose}
      maxWidthClass="max-w-6xl"
      headerActions={
        <div className="flex items-center gap-2">
          <CockpitButton onClick={() => setShowImports(true)}><Download size={12} className="mr-1 inline" />{t("imports.button")}</CockpitButton>
          <CockpitButton onClick={() => setShowISOs(true)}><Disc size={12} className="mr-1 inline" />{t("iso.title")}</CockpitButton>
          <CockpitButton onClick={refresh}><RefreshCw size={13} className={loading ? "animate-spin" : ""} /></CockpitButton>
          <CockpitButton tone="primary" onClick={() => setShowCreate(true)}><Plus size={13} className="mr-1 inline" />{t("new_vm")}</CockpitButton>
        </div>
      }
    >
      <div className="space-y-6">
        <p className="text-sm text-[#8d9ab0]">{t("subtitle")}</p>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <SummaryCard label={t("summary.total")} value={summary.total} />
          <SummaryCard label={t("summary.running")} value={summary.running} highlight />
          <SummaryCard label={t("summary.vcpu")} value={summary.cpu} />
          <SummaryCard label={t("summary.ram")} value={`${summary.ramGb.toFixed(1)} GB`} />
        </div>

        {error && <div className="rounded-[6px] border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>}

        {loading ? (
          <p className="text-sm text-[#8d9ab0]">{t("loading")}</p>
        ) : vms.length === 0 ? (
          <div className="rounded-[6px] border border-[#2a364b] bg-[#111827] p-10 text-center">
            <p className="text-sm text-[#8d9ab0]">{t("empty")} <span className="text-violet-300">{t("empty_cta")}</span> {t("empty_suffix")}</p>
            <p className="mt-2 text-xs text-[#5b6675]">{t("tip")} {t("tip_iso")}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
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
      </div>

      {showCreate && <CreateVMDialog onClose={() => setShowCreate(false)} onCreated={refresh} />}
      {editVm && <EditVMDialog vm={editVm} onClose={() => setEditVm(null)} onSaved={async () => { setEditVm(null); await refresh() }} />}
      {showISOs && <ISOLibraryPanel onClose={() => setShowISOs(false)} />}
      {consoleVm && <VMConsoleModal vm={consoleVm} onClose={() => setConsoleVm(null)} />}
      {snapshotVm && <SnapshotsPanel vm={snapshotVm} onClose={() => setSnapshotVm(null)} />}
      {showImports && <ImportJobsPanel onClose={() => setShowImports(false)} />}
      {logsVm && <VMLogsPanel vm={logsVm} onClose={() => setLogsVm(null)} />}
    </AdminOverlay>
  )
}

function SummaryCard({ label, value, highlight }: { label: string; value: number | string; highlight?: boolean }) {
  return (
    <div className={`rounded-[6px] border p-4 ${highlight ? "border-emerald-500/30 bg-emerald-500/5" : "border-[#2a364b] bg-[#111827]"}`}>
      <p className="text-[11px] uppercase tracking-wider text-[#8d9ab0]">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${highlight ? "text-emerald-200" : "text-[#e8eef8]"}`}>{value}</p>
    </div>
  )
}
