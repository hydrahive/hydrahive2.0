import { useCallback, useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { CircleSlash, Plus, RefreshCw, Server, Wifi } from "lucide-react"
import { HelpButton } from "@/i18n/HelpButton"
import { nodesApi } from "@/features/nodes/api"
import { NodeCard } from "@/features/nodes/NodeCard"
import { EnrollNodeDialog } from "@/features/nodes/EnrollNodeDialog"
import { ApproveNodeDialog } from "@/features/nodes/ApproveNodeDialog"
import { NodeDetailDialog } from "@/features/nodes/NodeDetailDialog"
import type { ComputeNode } from "@/features/nodes/types"
import { CockpitButton } from "../CockpitButton"
import { AdminConfirmDialog, AdminFeedback, AdminStat } from "./ui"
import { AdminOverlay } from "./AdminOverlay"

const POLL_MS = 5000

type ConfirmKind = "drain" | "disable" | "revoke"

export function NodesOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("nodes")
  const [nodes, setNodes] = useState<ComputeNode[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [showEnroll, setShowEnroll] = useState(false)
  const [approveNode, setApproveNode] = useState<ComputeNode | null>(null)
  const [detailNode, setDetailNode] = useState<ComputeNode | null>(null)
  const [confirm, setConfirm] = useState<{ kind: ConfirmKind; node: ComputeNode } | null>(null)

  const refresh = useCallback(async () => {
    try {
      setNodes(await nodesApi.list())
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
    const interval = window.setInterval(refresh, POLL_MS)
    return () => window.clearInterval(interval)
  }, [refresh])

  const summary = useMemo(() => ({
    total: nodes.length,
    online: nodes.filter((n) => n.status === "online").length,
    pending: nodes.filter((n) => n.status === "pending").length,
    offline: nodes.filter((n) => n.status === "offline" || n.status === "revoked" || n.status === "disabled").length,
  }), [nodes])

  const runAction = useCallback(async (node: ComputeNode, action: (id: string) => Promise<ComputeNode>) => {
    setBusyId(node.node_id)
    setError(null)
    try {
      await action(node.node_id)
      await refresh()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusyId(null)
    }
  }, [refresh])

  const confirmAction = async () => {
    if (!confirm) return
    const { kind, node } = confirm
    setConfirm(null)
    const map = { drain: nodesApi.drain, disable: nodesApi.disable, revoke: nodesApi.revoke }
    await runAction(node, map[kind])
  }

  return (
    <AdminOverlay
      eyebrow="Admin"
      title={t("title")}
      onClose={onClose}
      maxWidthClass="max-w-6xl"
      headerActions={
        <div className="flex items-center gap-2">
          <HelpButton topic="nodes" />
          <CockpitButton onClick={refresh} title={t("refresh")} aria-label={t("refresh")}>
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          </CockpitButton>
          <CockpitButton tone="primary" onClick={() => setShowEnroll(true)}>
            <Plus size={13} className="mr-1 inline" />{t("actions.enroll")}
          </CockpitButton>
        </div>
      }
    >
      <div className="space-y-6">
        <p className="text-sm text-[#8d9ab0]">{t("subtitle")}</p>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <AdminStat icon={Server} label={t("summary.total")} value={summary.total} />
          <AdminStat icon={Wifi} label={t("summary.online")} value={summary.online} />
          <AdminStat icon={RefreshCw} label={t("summary.pending")} value={summary.pending} />
          <AdminStat icon={CircleSlash} label={t("summary.offline")} value={summary.offline} />
        </div>

        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}

        {loading ? (
          <AdminFeedback loading>{t("loading")}</AdminFeedback>
        ) : nodes.length === 0 ? (
          <div className="rounded-[6px] border border-[#2a364b] bg-[#111827] p-10 text-center">
            <Server size={28} className="mx-auto mb-3 text-[#5b6675]" />
            <p className="text-sm text-[#8d9ab0]">{t("empty")}</p>
            <p className="mt-2 text-xs text-[#5b6675]">{t("empty_hint")}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {nodes.map((node) => (
              <NodeCard
                key={node.node_id}
                node={node}
                busy={busyId === node.node_id}
                onApprove={() => setApproveNode(node)}
                onDrain={() => setConfirm({ kind: "drain", node })}
                onDisable={() => setConfirm({ kind: "disable", node })}
                onEnable={() => runAction(node, nodesApi.enable)}
                onRevoke={() => setConfirm({ kind: "revoke", node })}
                onDetails={() => setDetailNode(node)}
              />
            ))}
          </div>
        )}
      </div>

      {showEnroll && <EnrollNodeDialog onClose={() => setShowEnroll(false)} onCreated={refresh} />}
      {approveNode && (
        <ApproveNodeDialog
          node={approveNode}
          onClose={() => setApproveNode(null)}
          onApproved={async () => { setApproveNode(null); await refresh() }}
        />
      )}
      {detailNode && <NodeDetailDialog node={detailNode} onClose={() => setDetailNode(null)} />}
      {confirm && (
        <AdminConfirmDialog
          title={t(`confirm.${confirm.kind}_title`)}
          confirmLabel={t("confirm.confirm")}
          cancelLabel={t("confirm.cancel")}
          confirmTone={confirm.kind === "revoke" ? "danger" : "primary"}
          onConfirm={confirmAction}
          onClose={() => setConfirm(null)}
        >
          {t(`confirm.${confirm.kind}_body`)}
        </AdminConfirmDialog>
      )}
    </AdminOverlay>
  )
}
