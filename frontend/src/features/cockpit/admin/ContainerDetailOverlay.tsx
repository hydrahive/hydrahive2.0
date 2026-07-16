import { useEffect, useState, type ReactNode } from "react"
import { FileText, Gauge, Settings, Terminal as TerminalIcon } from "lucide-react"
import { useTranslation } from "react-i18next"
import { containersApi } from "@/features/containers/api"
import type { Container } from "@/features/containers/types"
import { ContainerStatusBadge } from "@/features/containers/StatusBadge"
import { ConsolePane } from "@/features/containers/ConsolePane"
import { ContainerLogPane } from "@/features/containers/ContainerLogPane"
import { ContainerStatsPane } from "@/features/containers/ContainerStatsPane"
import { ContainerConfigPane } from "@/features/containers/ContainerConfigPane"
import { AdminFeedback } from "./ui"
import { AdminOverlay } from "./AdminOverlay"

type Tab = "console" | "logs" | "stats" | "config"

export function ContainerDetailOverlay({ containerId, onClose }: { containerId: string; onClose: () => void }) {
  const { t } = useTranslation("containers")
  const [container, setContainer] = useState<Container | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>("console")

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const nextContainer = await containersApi.get(containerId)
        if (active) { setContainer(nextContainer); setError(null) }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : String(reason))
      }
    }
    void load()
    const interval = window.setInterval(load, 5000)
    return () => { active = false; window.clearInterval(interval) }
  }, [containerId])

  const running = container?.actual_state === "running"

  return (
    <AdminOverlay
      eyebrow="Admin · Container"
      title={container?.name ?? "Container-Details"}
      onClose={onClose}
      maxWidthClass="max-w-6xl"
      headerActions={container ? <ContainerStatusBadge state={container.actual_state} /> : undefined}
    >
      {error ? <AdminFeedback tone="danger">{error}</AdminFeedback> : !container ? (
        <AdminFeedback loading>{t("detail.loading")}</AdminFeedback>
      ) : (
        <div className="flex h-full min-h-[32rem] flex-col gap-3">
          <p className="shrink-0 truncate font-mono text-xs text-[#8d9ab0]">{container.image}</p>
          <div className="flex shrink-0 items-center gap-1 border-b border-[#2a364b]" role="tablist">
            <TabButton active={tab === "console"} onClick={() => setTab("console")} disabled={!running}><TerminalIcon size={12} />{t("tabs.console")}</TabButton>
            <TabButton active={tab === "logs"} onClick={() => setTab("logs")}><FileText size={12} />{t("tabs.logs")}</TabButton>
            <TabButton active={tab === "stats"} onClick={() => setTab("stats")}><Gauge size={12} />{t("tabs.stats")}</TabButton>
            <TabButton active={tab === "config"} onClick={() => setTab("config")}><Settings size={12} />{t("tabs.config")}</TabButton>
          </div>
          <div className="min-h-0 flex-1 overflow-hidden rounded-[6px] border border-[#2a364b] bg-[#0e1420]">
            {tab === "console" && running && <ConsolePane containerId={container.container_id} className="h-full" />}
            {tab === "console" && !running && <div className="grid h-full place-items-center"><AdminFeedback>{t("detail.console_not_running")}</AdminFeedback></div>}
            {tab === "logs" && <ContainerLogPane containerId={container.container_id} />}
            {tab === "stats" && <ContainerStatsPane container={container} />}
            {tab === "config" && <ContainerConfigPane containerId={container.container_id} />}
          </div>
        </div>
      )}
    </AdminOverlay>
  )
}

function TabButton({ active, onClick, disabled, children }: { active: boolean; onClick: () => void; disabled?: boolean; children: ReactNode }) {
  return (
    <button type="button" role="tab" aria-selected={active} onClick={onClick} disabled={disabled}
      className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-bold transition-colors disabled:cursor-not-allowed disabled:opacity-30 ${active ? "border-[#69d7ff] text-[#c8f2ff]" : "border-transparent text-[#8d9ab0] hover:text-[#e8eef8]"}`}>
      {children}
    </button>
  )
}
