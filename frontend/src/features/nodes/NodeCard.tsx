import { Cpu, HardDrive, MemoryStick, Server, ShieldCheck } from "lucide-react"
import { useTranslation } from "react-i18next"
import { CockpitButton } from "@/features/cockpit/CockpitButton"
import { NodeStatusBadge } from "./NodeStatusBadge"
import { nodeCapabilities, nodeResources, timeAgo } from "./format"
import type { ComputeNode } from "./types"

interface Props {
  node: ComputeNode
  busy?: boolean
  onApprove?: () => void
  onDrain?: () => void
  onDisable?: () => void
  onEnable?: () => void
  onRevoke?: () => void
  onDetails?: () => void
}

export function NodeCard({ node, busy = false, onApprove, onDrain, onDisable, onEnable, onRevoke, onDetails }: Props) {
  const { t } = useTranslation("nodes")
  const res = nodeResources(node)
  const caps = nodeCapabilities(node)
  const isLocal = node.kind === "local"

  return (
    <div className="rounded-[6px] border border-[#2a364b] bg-[#111827] p-4">
      <div className="flex items-start gap-3">
        <Server size={18} className="mt-0.5 shrink-0 text-[#69d7ff]" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-sm font-bold text-[#e8eef8]">{node.name}</h3>
            <span className="rounded-[3px] border border-[#2a364b] bg-[#172133] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#8d9ab0]">
              {t(`kind.${node.kind}`, { defaultValue: node.kind })}
            </span>
          </div>
          <p className="mt-0.5 truncate font-mono text-[11px] text-[#5b6675]">{node.node_id}</p>
        </div>
        <NodeStatusBadge status={node.status} pulse />
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2 text-[11px] text-[#8d9ab0]">
        <span className="inline-flex items-center gap-1"><Cpu size={12} className="text-[#5b6675]" />{res.cpu_cores ?? "–"} {t("card.cpu")}</span>
        <span className="inline-flex items-center gap-1"><MemoryStick size={12} className="text-[#5b6675]" />{res.memory_mb ? `${Math.round(res.memory_mb / 1024)}G` : "–"}</span>
        <span className="inline-flex items-center gap-1"><HardDrive size={12} className="text-[#5b6675]" />{res.storage_gb ? `${res.storage_gb}G` : "–"}</span>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-[#5b6675]">
        <span>{t("card.incus")}: <span className="text-[#8d9ab0]">{caps.incus ? t("card.yes") : t("card.no")}</span></span>
        <span>{t("card.kvm")}: <span className="text-[#8d9ab0]">{caps.kvm ? t("card.yes") : t("card.no")}</span></span>
        {!isLocal && <span>{t("card.last_seen")}: <span className="text-[#8d9ab0]">{timeAgo(node.last_seen_at, t("card.never"))}</span></span>}
        {node.agent_version && <span>{t("card.agent_version")}: <span className="text-[#8d9ab0]">{node.agent_version}</span></span>}
      </div>

      {node.health_errors.length > 0 && (
        <div className="mt-2 rounded-[4px] border border-amber-500/25 bg-amber-500/[6%] px-2 py-1 text-[11px] text-amber-300">
          {node.health_errors.slice(0, 2).join(" · ")}
        </div>
      )}

      {!isLocal && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {node.status === "pending" && (
            <CockpitButton tone="primary" onClick={onApprove} disabled={busy}>
              <ShieldCheck size={12} className="mr-1 inline" />{t("actions.approve")}
            </CockpitButton>
          )}
          {(node.status === "online" || node.status === "degraded") && (
            <CockpitButton onClick={onDrain} disabled={busy}>{t("actions.drain")}</CockpitButton>
          )}
          {node.status !== "disabled" && node.status !== "pending" && node.status !== "revoked" && (
            <CockpitButton onClick={onDisable} disabled={busy}>{t("actions.disable")}</CockpitButton>
          )}
          {(node.status === "disabled" || node.status === "draining") && (
            <CockpitButton onClick={onEnable} disabled={busy}>{t("actions.enable")}</CockpitButton>
          )}
          <button
            type="button"
            onClick={onDetails}
            className="ml-auto rounded-[4px] px-2 py-1 text-[11px] text-[#8d9ab0] hover:text-[#e8eef8]"
          >
            {t("card.details")}
          </button>
          {node.status !== "revoked" && (
            <CockpitButton tone="danger" onClick={onRevoke} disabled={busy}>{t("actions.revoke")}</CockpitButton>
          )}
        </div>
      )}
      {isLocal && onDetails && (
        <div className="mt-3 flex justify-end">
          <button type="button" onClick={onDetails} className="rounded-[4px] px-2 py-1 text-[11px] text-[#8d9ab0] hover:text-[#e8eef8]">{t("card.details")}</button>
        </div>
      )}
    </div>
  )
}
