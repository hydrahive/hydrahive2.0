import { Cpu, HardDrive, MemoryStick, Network } from "lucide-react"
import { useEffect, useState } from "react"
import type { VM } from "./types"
import { StatusBadge } from "./StatusBadge"
import { formatRamMB } from "./format"
import { vmsApi } from "./api"
import { Bar, Spec } from "./_vmHelpers"
import { VMCardActions } from "./_VMCardActions"

interface Props {
  vm: VM
  onStart: () => Promise<void>
  onStop: () => Promise<void>
  onPoweroff: () => Promise<void>
  onDelete: () => Promise<void>
  onConsole: () => void
  onSnapshots: () => void
  onLogs: () => void
  onEdit: () => void
}

export function VMCard({ vm, onStart, onStop, onPoweroff, onDelete, onConsole, onSnapshots, onLogs, onEdit }: Props) {
  const [busy, setBusy] = useState(false)
  const [stats, setStats] = useState<{ cpu_pct: number; rss_mb: number } | null>(null)

  useEffect(() => {
    if (vm.actual_state !== "running") { setStats(null); return }
    let alive = true
    async function tick() {
      try {
        const s = await vmsApi.stats(vm.vm_id)
        if (alive && s.alive) setStats({ cpu_pct: s.cpu_pct, rss_mb: s.rss_mb })
      } catch { /* ignore */ }
    }
    void tick()
    const t = setInterval(tick, 3000)
    return () => { alive = false; clearInterval(t) }
  }, [vm.vm_id, vm.actual_state])

  async function withBusy(fn: () => Promise<void>) {
    if (busy) return
    setBusy(true)
    try { await fn() } finally { setBusy(false) }
  }

  const running = vm.actual_state === "running"
  const transitioning = vm.actual_state === "starting" || vm.actual_state === "stopping"
  const canStart = vm.actual_state === "stopped" || vm.actual_state === "created" || vm.actual_state === "error"

  return (
    <div className="rounded-xl border border-white/[8%] bg-white/[2%] p-4 space-y-3 hover:border-white/[14%] transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-zinc-100 truncate">{vm.name}</p>
          {vm.description && (
            <p className="text-xs text-zinc-500 truncate mt-0.5">{vm.description}</p>
          )}
        </div>
        <StatusBadge state={vm.actual_state} />
      </div>

      <div className="flex flex-wrap gap-2 text-[11px]">
        <Spec icon={Cpu} label={`${vm.cpu} vCPU`} />
        <Spec icon={MemoryStick} label={formatRamMB(vm.ram_mb)} />
        <Spec icon={HardDrive} label={`${vm.disk_gb} GB`} />
        <Spec icon={Network} label={vm.network_mode} />
        {vm.iso_filename && <Spec label={vm.iso_filename} />}
      </div>

      {stats && (
        <div className="grid grid-cols-2 gap-3 text-[11px]">
          <Bar label="CPU" pct={Math.min(100, stats.cpu_pct / vm.cpu)} suffix={`${stats.cpu_pct.toFixed(1)}%`} color="violet" />
          <Bar label="RAM" pct={Math.min(100, (stats.rss_mb / vm.ram_mb) * 100)} suffix={`${stats.rss_mb} / ${vm.ram_mb} MB`} color="emerald" />
        </div>
      )}

      {vm.last_error_code && vm.actual_state === "error" && (
        <div className="text-[11px] text-rose-300 bg-rose-500/10 border border-rose-500/20 rounded-md px-2 py-1">
          {vm.last_error_code}
          {vm.last_error_params && Object.keys(vm.last_error_params).length > 0 && (
            <span className="text-rose-400/70"> — {JSON.stringify(vm.last_error_params)}</span>
          )}
        </div>
      )}

      <VMCardActions
        vmName={vm.name}
        busy={busy} running={running} canStart={canStart} transitioning={transitioning}
        onStart={() => withBusy(onStart)}
        onStop={() => withBusy(onStop)}
        onPoweroff={() => withBusy(onPoweroff)}
        onDelete={() => {
          if (confirm(`VM "${vm.name}" wirklich löschen? qcow2-Disk wird mit gelöscht.`)) withBusy(onDelete)
        }}
        onConsole={onConsole}
        onSnapshots={onSnapshots}
        onLogs={onLogs}
        onEdit={onEdit}
      />
    </div>
  )
}
