import { Box, Cpu, MemoryStick, Network, Play, RotateCw, Square, Terminal, Trash2 } from "lucide-react"
import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import type { Container, ContainerInfo } from "./types"
import { ContainerStatusBadge } from "./StatusBadge"
import { ContainerConsoleModal } from "./ContainerConsoleModal"
import { containersApi } from "./api"

interface Props {
  container: Container
  onStart: () => Promise<void>
  onStop: () => Promise<void>
  onRestart: () => Promise<void>
  onDelete: () => Promise<void>
}

export function ContainerCard({ container: c, onStart, onStop, onRestart, onDelete }: Props) {
  const [busy, setBusy] = useState(false)
  const [info, setInfo] = useState<ContainerInfo | null>(null)
  const [showConsole, setShowConsole] = useState(false)

  async function withBusy(fn: () => Promise<void>) {
    if (busy) return
    setBusy(true)
    try { await fn() } finally { setBusy(false) }
  }

  useEffect(() => {
    if (c.actual_state !== "running") { setInfo(null); return }
    let alive = true
    async function tick() {
      try {
        const i = await containersApi.info(c.container_id)
        if (alive) setInfo(i)
      } catch { /* */ }
    }
    void tick()
    const t = setInterval(tick, 4000)
    return () => { alive = false; clearInterval(t) }
  }, [c.container_id, c.actual_state])

  const running = c.actual_state === "running"
  const transitioning = c.actual_state === "starting" || c.actual_state === "stopping"
  const canStart = c.actual_state === "stopped" || c.actual_state === "error"

  return (
    <div className="rounded-xl border border-white/[8%] bg-white/[2%] p-4 space-y-3 hover:border-white/[14%] transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <Box size={14} className="text-violet-400 flex-shrink-0" />
            <Link to={`/containers/${c.container_id}`}
              className="text-sm font-semibold text-zinc-100 truncate hover:text-violet-200 hover:underline">
              {c.name}
            </Link>
          </div>
          {c.description && <p className="text-xs text-zinc-500 truncate mt-0.5 ml-5">{c.description}</p>}
          <p className="text-[11px] text-zinc-500 font-mono ml-5 mt-0.5">{c.image}</p>
        </div>
        <ContainerStatusBadge state={c.actual_state} />
      </div>

      <div className="flex flex-wrap gap-2 text-[11px]">
        <Spec icon={Cpu} label={c.cpu ? `${c.cpu} vCPU` : "CPU ∞"} />
        <Spec icon={MemoryStick} label={c.ram_mb ? `${c.ram_mb} MB` : "RAM ∞"} />
        <Spec icon={Network} label={c.network_mode} />
        {info?.ipv4 && <Spec label={info.ipv4} highlight />}
      </div>

      {info?.alive && info.memory_bytes != null && c.ram_mb && (
        <div className="text-[11px] text-zinc-400">
          <div className="flex items-baseline justify-between">
            <span>RAM</span>
            <span className="font-mono">{Math.round(info.memory_bytes / 1024 / 1024)} / {c.ram_mb} MB</span>
          </div>
          <div className="mt-0.5 h-1 rounded-full bg-zinc-800 overflow-hidden">
            <div className="h-full bg-emerald-500 transition-all"
              style={{ width: `${Math.min(100, info.memory_bytes / 1024 / 1024 / c.ram_mb * 100)}%` }} />
          </div>
        </div>
      )}

      {c.last_error_code && c.actual_state === "error" && (
        <div className="text-[11px] text-rose-300 bg-rose-500/10 border border-rose-500/20 rounded-md px-2 py-1">
          {c.last_error_code}
        </div>
      )}

      <div className="flex items-center gap-2 pt-1">
        {canStart && (
          <button disabled={busy || transitioning} onClick={() => withBusy(onStart)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-200 disabled:opacity-40">
            <Play size={12} /> Start
          </button>
        )}
        {running && (
          <>
            <button disabled={busy} onClick={() => setShowConsole(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/30 text-indigo-200 disabled:opacity-40">
              <Terminal size={12} /> Console
            </button>
            <button disabled={busy || transitioning} onClick={() => withBusy(onRestart)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-violet-500/15 hover:bg-violet-500/25 border border-violet-500/30 text-violet-200 disabled:opacity-40">
              <RotateCw size={12} /> Restart
            </button>
            <button disabled={busy || transitioning} onClick={() => withBusy(onStop)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-200 disabled:opacity-40">
              <Square size={12} /> Stop
            </button>
          </>
        )}
        <div className="flex-1" />
        {!running && !transitioning && (
          <button disabled={busy} onClick={() => {
            if (confirm(`Container "${c.name}" wirklich löschen? Daten sind weg.`)) withBusy(onDelete)
          }}
            className="p-1.5 rounded-lg text-zinc-500 hover:text-rose-300 hover:bg-rose-500/10" title="Löschen">
            <Trash2 size={12} />
          </button>
        )}
      </div>

      {showConsole && (
        <ContainerConsoleModal container={c} onClose={() => setShowConsole(false)} />
      )}
    </div>
  )
}

function Spec({ icon: Icon, label, highlight }: { icon?: React.ComponentType<{ size?: number; className?: string }>; label: string; highlight?: boolean }) {
  const cls = highlight
    ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-200"
    : "bg-white/[4%] border-white/[6%] text-zinc-400"
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border ${cls}`}>
      {Icon && <Icon size={11} />}
      {label}
    </span>
  )
}
