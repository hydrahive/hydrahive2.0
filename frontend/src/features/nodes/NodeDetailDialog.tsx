import { useTranslation } from "react-i18next"
import { Server } from "lucide-react"
import { AdminDialog } from "@/features/cockpit/admin/ui/AdminDialog"
import { AdminCodeBlock } from "@/features/cockpit/admin/ui/AdminFeedback"
import { NodeStatusBadge } from "./NodeStatusBadge"
import { nodeCapabilities, nodeResources, shortDateTime } from "./format"
import type { ComputeNode } from "./types"

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-[#1c2637] py-1.5 last:border-0">
      <span className="text-[11px] uppercase tracking-wider text-[#5b6675]">{label}</span>
      <span className="min-w-0 truncate text-right text-sm text-[#d4deeb]">{value}</span>
    </div>
  )
}

export function NodeDetailDialog({ node, onClose }: { node: ComputeNode; onClose: () => void }) {
  const { t } = useTranslation("nodes")
  const res = nodeResources(node)
  const caps = nodeCapabilities(node)
  const labelEntries = Object.entries(node.labels ?? {})

  return (
    <AdminDialog
      eyebrow="Admin"
      title={node.name}
      icon={<Server size={16} />}
      onClose={onClose}
      maxWidthClass="max-w-2xl"
    >
      <div className="space-y-5">
        <div className="flex items-center gap-2">
          <NodeStatusBadge status={node.status} />
          <span className="rounded-[3px] border border-[#2a364b] bg-[#172133] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#8d9ab0]">
            {t(`kind.${node.kind}`, { defaultValue: node.kind })}
          </span>
        </div>

        <section>
          <h3 className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[#69d7ff]">{t("detail.identity")}</h3>
          <div className="rounded-[6px] border border-[#2a364b] bg-[#111827] px-3">
            <Row label="ID" value={<span className="font-mono text-xs">{node.node_id}</span>} />
            <Row label={t("card.protocol")} value={node.protocol_version} />
            {node.agent_version && <Row label={t("card.agent_version")} value={node.agent_version} />}
            <Row label={t("detail.created_at")} value={shortDateTime(node.created_at)} />
            <Row label={t("detail.updated_at")} value={shortDateTime(node.updated_at)} />
            {node.approved_by && <Row label={t("detail.approved_by")} value={node.approved_by} />}
            {node.approved_at && <Row label={t("detail.approved_at")} value={shortDateTime(node.approved_at)} />}
          </div>
        </section>

        <section>
          <h3 className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[#69d7ff]">{t("detail.resources")}</h3>
          <div className="rounded-[6px] border border-[#2a364b] bg-[#111827] px-3">
            <Row label={t("card.cpu")} value={res.cpu_cores ?? t("card.unknown")} />
            <Row label={t("card.memory")} value={res.memory_mb ? `${res.memory_mb} MB` : t("card.unknown")} />
            <Row label={t("card.storage")} value={res.storage_gb ? `${res.storage_gb} GB` : t("card.unknown")} />
          </div>
        </section>

        <section>
          <h3 className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[#69d7ff]">{t("detail.capabilities")}</h3>
          <div className="rounded-[6px] border border-[#2a364b] bg-[#111827] px-3">
            <Row label={t("card.incus")} value={caps.incus ? t("card.yes") : t("card.no")} />
            <Row label={t("card.kvm")} value={caps.kvm ? t("card.yes") : t("card.no")} />
          </div>
        </section>

        <section>
          <h3 className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[#69d7ff]">{t("detail.fingerprint")}</h3>
          {node.certificate_fingerprint
            ? <AdminCodeBlock>{node.certificate_fingerprint}</AdminCodeBlock>
            : <p className="text-xs text-[#5b6675]">{t("detail.no_fingerprint")}</p>}
        </section>

        <section>
          <h3 className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[#69d7ff]">{t("detail.health")}</h3>
          {node.health_errors.length === 0
            ? <p className="text-xs text-[#5b6675]">{t("detail.no_health_errors")}</p>
            : (
              <ul className="space-y-1">
                {node.health_errors.map((err, i) => (
                  <li key={i} className="rounded-[4px] border border-amber-500/25 bg-amber-500/[6%] px-2 py-1 text-[11px] text-amber-300">{err}</li>
                ))}
              </ul>
            )}
        </section>

        <section>
          <h3 className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-[#69d7ff]">{t("detail.labels")}</h3>
          {labelEntries.length === 0
            ? <p className="text-xs text-[#5b6675]">{t("detail.no_labels")}</p>
            : (
              <div className="flex flex-wrap gap-1.5">
                {labelEntries.map(([k, v]) => (
                  <span key={k} className="rounded-[3px] border border-[#2a364b] bg-[#172133] px-2 py-0.5 text-[11px] text-[#8d9ab0]">
                    {k}: <span className="text-[#d4deeb]">{String(v)}</span>
                  </span>
                ))}
              </div>
            )}
        </section>
      </div>
    </AdminDialog>
  )
}
