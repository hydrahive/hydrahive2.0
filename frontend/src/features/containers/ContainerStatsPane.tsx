import { useEffect, useState } from "react"
import { Cpu, MemoryStick, Network } from "lucide-react"
import type { Container, ContainerInfo } from "./types"
import { containersApi } from "./api"

interface Props {
  container: Container
}

export function ContainerStatsPane({ container: c }: Props) {
  const [info, setInfo] = useState<ContainerInfo | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (c.actual_state !== "running") { setInfo(null); return }
    let alive = true
    async function tick() {
      try {
        const i = await containersApi.info(c.container_id)
        if (alive) { setInfo(i); setError(null) }
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : String(e))
      }
    }
    void tick()
    const t = setInterval(tick, 3000)
    return () => { alive = false; clearInterval(t) }
  }, [c.container_id, c.actual_state])

  const memMb = info?.memory_bytes ? Math.round(info.memory_bytes / 1024 / 1024) : null
  const memPct = memMb && c.ram_mb ? Math.min(100, (memMb / c.ram_mb) * 100) : null

  return (
    <div className="p-6 space-y-5 overflow-auto h-full">
      {error && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-xs text-rose-200">{error}</div>
      )}
      {c.actual_state !== "running" ? (
        <p className="text-sm text-zinc-500">Container läuft nicht — keine Live-Stats.</p>
      ) : !info ? (
        <p className="text-sm text-zinc-500">Lade…</p>
      ) : (
        <>
          <Card icon={<MemoryStick size={14} className="text-violet-400" />} label="RAM">
            <div className="font-mono text-xs text-zinc-300">
              {memMb ?? "—"} MB
              {c.ram_mb && <span className="text-zinc-500"> / {c.ram_mb} MB</span>}
            </div>
            {memPct != null && (
              <div className="h-1.5 mt-2 rounded-full bg-zinc-800 overflow-hidden">
                <div className="h-full bg-emerald-500 transition-all" style={{ width: `${memPct}%` }} />
              </div>
            )}
            {info.memory_peak_bytes && (
              <p className="mt-1.5 text-[11px] text-zinc-500">
                Peak: {Math.round(info.memory_peak_bytes / 1024 / 1024)} MB
              </p>
            )}
          </Card>

          <Card icon={<Cpu size={14} className="text-violet-400" />} label="CPU">
            <div className="font-mono text-xs text-zinc-300">
              {(info.cpu_usage_ns ?? 0) / 1e9} s gesamt
            </div>
            <p className="mt-1 text-[11px] text-zinc-500">
              {c.cpu ? `Limit: ${c.cpu} vCPU` : "Kein Limit"}
            </p>
          </Card>

          <Card icon={<Network size={14} className="text-violet-400" />} label="Netzwerk">
            <div className="font-mono text-xs text-zinc-300">
              {info.ipv4 ?? "(keine IPv4)"} — {c.network_mode}
            </div>
          </Card>
        </>
      )}
    </div>
  )
}

function Card({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-white/[8%] bg-white/[2%] p-4">
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <p className="text-[11px] uppercase tracking-wider text-zinc-500">{label}</p>
      </div>
      {children}
    </div>
  )
}
