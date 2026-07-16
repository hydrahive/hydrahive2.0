import { useEffect, useState } from "react"
import { Cpu, MemoryStick, Network } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminFeedback, AdminPanel } from "@/features/cockpit/admin/ui"
import type { Container, ContainerInfo } from "./types"
import { containersApi } from "./api"

interface Props {
  container: Container
}

export function ContainerStatsPane({ container: currentContainer }: Props) {
  const { t } = useTranslation("containers")
  const [info, setInfo] = useState<ContainerInfo | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (currentContainer.actual_state !== "running") {
      const clear = window.setTimeout(() => setInfo(null), 0)
      return () => window.clearTimeout(clear)
    }
    let active = true
    async function tick() {
      try {
        const nextInfo = await containersApi.info(currentContainer.container_id)
        if (active) { setInfo(nextInfo); setError(null) }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : String(reason))
      }
    }
    void tick()
    const interval = setInterval(tick, 3000)
    return () => { active = false; clearInterval(interval) }
  }, [currentContainer.container_id, currentContainer.actual_state])

  const memoryMb = info?.memory_bytes ? Math.round(info.memory_bytes / 1024 / 1024) : null
  const memoryPercent = memoryMb && currentContainer.ram_mb
    ? Math.min(100, (memoryMb / currentContainer.ram_mb) * 100)
    : null

  return (
    <div className="h-full space-y-4 overflow-auto p-6">
      {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
      {currentContainer.actual_state !== "running" ? (
        <AdminFeedback>{t("stats.not_running")}</AdminFeedback>
      ) : !info ? (
        <AdminFeedback loading>{t("loading")}</AdminFeedback>
      ) : (
        <>
          <AdminPanel title="RAM" icon={MemoryStick}>
            <div className="font-mono text-xs text-[#b9c5d6]">
              {memoryMb ?? "—"} MB
              {currentContainer.ram_mb && <span className="text-[#8d9ab0]"> / {currentContainer.ram_mb} MB</span>}
            </div>
            {memoryPercent != null && (
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[#0b111c]">
                <div className="h-full bg-[#69d7ff] transition-all" style={{ width: `${memoryPercent}%` }} />
              </div>
            )}
            {info.memory_peak_bytes && (
              <p className="mt-1.5 text-[11px] text-[#8d9ab0]">
                Peak: {Math.round(info.memory_peak_bytes / 1024 / 1024)} MB
              </p>
            )}
          </AdminPanel>

          <AdminPanel title="CPU" icon={Cpu}>
            <div className="font-mono text-xs text-[#b9c5d6]">{(info.cpu_usage_ns ?? 0) / 1e9} s gesamt</div>
            <p className="mt-1 text-[11px] text-[#8d9ab0]">
              {currentContainer.cpu ? t("spec.cpu_limit", { cpu: currentContainer.cpu }) : t("spec.no_limit")}
            </p>
          </AdminPanel>

          <AdminPanel title="Netzwerk" icon={Network}>
            <div className="font-mono text-xs text-[#b9c5d6]">
              {info.ipv4 ?? t("spec.no_ipv4")} — {currentContainer.network_mode}
            </div>
          </AdminPanel>
        </>
      )}
    </div>
  )
}
