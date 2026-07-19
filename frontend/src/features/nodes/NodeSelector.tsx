import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { AdminField, adminInputClass } from "@/features/cockpit/admin/ui/AdminField"
import { nodesApi } from "./api"
import { isPlaceableStatus } from "./NodeStatusBadge"
import type { ComputeNode } from "./types"

interface Props {
  value: string
  onChange: (nodeId: string) => void
  /** Only placement-capable nodes (online) are selectable; others are shown disabled with a reason. */
  requireCapability?: "incus" | "kvm"
  disabled?: boolean
}

function nodeCapable(node: ComputeNode, capability?: "incus" | "kvm"): boolean {
  if (!capability) return true
  return Boolean((node.capabilities as Record<string, unknown>)[capability])
}

/**
 * Target compute node picker. Default selection is always the local node.
 * Remote nodes are selectable only when online and capable; unsuitable nodes
 * are rendered disabled with a short reason so the user understands why.
 */
export function NodeSelector({ value, onChange, requireCapability, disabled = false }: Props) {
  const { t } = useTranslation("nodes")
  const [nodes, setNodes] = useState<ComputeNode[]>([])
  const [error, setError] = useState(false)

  useEffect(() => {
    let active = true
    nodesApi.list()
      .then((list) => { if (active) setNodes(list) })
      .catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [])

  // Local host is always present even if the node list fails to load.
  const hasLocal = nodes.some((n) => n.node_id === "local")
  const options = hasLocal || error
    ? nodes
    : [{ node_id: "local", name: t("kind.local"), status: "online", kind: "local", capabilities: { incus: true } } as unknown as ComputeNode, ...nodes]

  return (
    <AdminField label={t("selector.label", { defaultValue: "Ziel-Node" })} help={t("selector.hint", { defaultValue: "Standard ist der lokale Host. Remote-Nodes müssen online und geeignet sein." })}>
      <select
        className={adminInputClass}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      >
        {options.map((node) => {
          const placeable = isPlaceableStatus(node.status) || node.node_id === "local"
          const capable = nodeCapable(node, requireCapability)
          const selectable = placeable && capable
          const reason = !placeable
            ? t(`status.${node.status}`, { defaultValue: node.status })
            : !capable
              ? t(`card.${requireCapability}`, { defaultValue: requireCapability })
              : ""
          return (
            <option key={node.node_id} value={node.node_id} disabled={!selectable && node.node_id !== value}>
              {node.name}{node.node_id === "local" ? "" : ` · ${t(`kind.${node.kind}`, { defaultValue: node.kind })}`}{reason ? ` (${reason})` : ""}
            </option>
          )
        })}
      </select>
    </AdminField>
  )
}
