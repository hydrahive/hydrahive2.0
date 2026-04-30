import { Camera, Cpu, HardDrive, MemoryStick, Monitor, Network, Play, Power, Square, Trash2 } from "lucide-react"
import { useState } from "react"
import type { VM } from "./types"
import { StatusBadge } from "./StatusBadge"
import { formatRamMB } from "./format"

interface Props {
  vm: VM
  onStart: () => Promise<void>
  onStop: () => Promise<void>
  onPoweroff: () => Promise<void>
  onDelete: () => Promise<void>
  onConsole: () => void
  onSnapshots: () => void
}

export function VMCard({ vm, onStart, onStop, onPoweroff, onDelete, onConsole, onSnapshots }: Props) {
  const [busy, setBusy] = useState(false)

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

      {vm.last_error_code && vm.actual_state === "error" && (
        <div className="text-[11px] text-rose-300 bg-rose-500/10 border border-rose-500/20 rounded-md px-2 py-1">
          {vm.last_error_code}
          {vm.last_error_params && Object.keys(vm.last_error_params).length > 0 && (
            <span className="text-rose-400/70"> — {JSON.stringify(vm.last_error_params)}</span>
          )}
        </div>
      )}

      <div className="flex items-center gap-2 pt-1">
        {canStart && (
          <button
            disabled={busy || transitioning}
            onClick={() => withBusy(onStart)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-200 disabled:opacity-40 transition-colors"
          >
            <Play size={12} /> Start
          </button>
        )}
        {running && (
          <>
            <button
              onClick={onConsole}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-violet-500/15 hover:bg-violet-500/25 border border-violet-500/30 text-violet-200 transition-colors"
              title="VNC-Konsole im Browser öffnen"
            >
              <Monitor size={12} /> Konsole
            </button>
            <button
              disabled={busy || transitioning}
              onClick={() => withBusy(onStop)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-200 disabled:opacity-40 transition-colors"
              title="Graceful Shutdown (ACPI)"
            >
              <Square size={12} /> Stop
            </button>
            <button
              disabled={busy || transitioning}
              onClick={() => withBusy(onPoweroff)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-rose-200 disabled:opacity-40 transition-colors"
              title="Hard Power-Off (SIGKILL)"
            >
              <Power size={12} /> Aus
            </button>
          </>
        )}
        <div className="flex-1" />
        <button
          onClick={onSnapshots}
          className="flex items-center gap-1.5 p-1.5 rounded-lg text-xs text-zinc-500 hover:text-zinc-200 hover:bg-white/5 transition-colors"
          title="Snapshots"
        >
          <Camera size={12} />
        </button>
        {!running && !transitioning && (
          <button
            disabled={busy}
            onClick={() => {
              if (confirm(`VM "${vm.name}" wirklich löschen? qcow2-Disk wird mit gelöscht.`)) {
                withBusy(onDelete)
              }
            }}
            className="flex items-center gap-1.5 p-1.5 rounded-lg text-xs text-zinc-500 hover:text-rose-300 hover:bg-rose-500/10 transition-colors"
            title="Löschen"
          >
            <Trash2 size={12} />
          </button>
        )}
      </div>
    </div>
  )
}

function Spec({ icon: Icon, label }: { icon?: React.ComponentType<{ size?: number; className?: string }>; label: string }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-white/[4%] border border-white/[6%] text-zinc-400">
      {Icon && <Icon size={11} />}
      {label}
    </span>
  )
}
