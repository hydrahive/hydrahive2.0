/* Agenten-Baum: wer hat wen beauftragt, was tut jeder gerade, was kostet es.
   Till 20.11.2026: „ich sehe in keinster Weise, was die Agenten tun“. Zeigt alle
   Ebenen (nicht nur direkte Aufträge), Kosten je Agent, die letzten Befehle im
   Klartext und riskante/gesperrte Befehle rot. Lädt alle 5 s neu, solange offen. */
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { delegationsApi, type AgentTree, type TreeNode, type TreeTool } from "./delegationsApi"

const usd = (v: number) => `${v.toFixed(2)} $`

export function ToolLine({ tool }: { tool: TreeTool }) {
  const { t } = useTranslation("chat")
  const bad = tool.risky || tool.blocked
  return (
    <div className={`truncate font-mono text-[11px] ${bad ? "text-rose-300" : "text-zinc-400"}`} title={tool.label}>
      {tool.at.slice(11, 19)} {bad ? (tool.blocked ? `⛔ ${t("delegation.tree.blocked")} ` : "⚠ ") : ""}
      {tool.tool}{tool.label ? `: ${tool.label}` : ""}
    </div>
  )
}

export function TreeNodeView({ node, onCancel }: { node: TreeNode; onCancel: (id: string) => void }) {
  const { t } = useTranslation("chat")
  const [open, setOpen] = useState(node.status === "running")
  const running = node.status === "running"
  return (
    <div className="border-l border-s-rand pl-3 py-0.5">
      <div className="flex items-center gap-2">
        <button onClick={() => setOpen(!open)} className="text-zinc-500 w-3 text-left">{open ? "▾" : "▸"}</button>
        <span className="font-medium">{node.target_name}</span>
        <span className={running ? "text-sky-300" : "text-zinc-500"}>{t(`delegation.status.${node.status}`)}</span>
        <span className="text-zinc-400">
          {t("delegation.tree.stats", { cost: usd(node.cost.cost_usd), calls: node.cost.calls, tools: node.tool_count })}
          {node.cost.model ? ` · ${node.cost.model}` : ""}
        </span>
        {node.flagged_tools.length > 0 && (
          <span className="text-rose-300">⚠ {node.flagged_tools.length}</span>
        )}
        {running && (
          <button onClick={() => onCancel(node.id)} className="ml-auto text-zinc-500 hover:text-rose-300">
            {t("delegation.cancel")}
          </button>
        )}
      </div>
      {open && (
        <div className="pl-5 space-y-0.5">
          <div className="text-zinc-500 truncate" title={node.task}>{node.task}</div>
          {node.flagged_tools.length > 0 && (
            <div>
              <div className="text-rose-300">{t("delegation.tree.flagged")}</div>
              {node.flagged_tools.map((x, i) => <ToolLine key={`f${i}`} tool={x} />)}
            </div>
          )}
          {node.recent_tools.length > 0 && <div className="text-zinc-500">{t("delegation.tree.recent")}</div>}
          {node.recent_tools.map((x, i) => <ToolLine key={`r${i}`} tool={x} />)}
          {node.children.map((c) => <TreeNodeView key={c.id} node={c} onCancel={onCancel} />)}
        </div>
      )}
    </div>
  )
}

export function AgentTreePanel({ sessionId, onChanged }: { sessionId: string; onChanged: () => void }) {
  const { t } = useTranslation("chat")
  const [tree, setTree] = useState<AgentTree | null>(null)

  useEffect(() => {
    let alive = true
    const load = () => delegationsApi.tree(sessionId).then((r) => { if (alive) setTree(r) }).catch(() => {})
    void load()
    const timer = setInterval(load, 5000)
    return () => { alive = false; clearInterval(timer) }
  }, [sessionId])

  const cancel = async (id: string) => {
    await delegationsApi.cancel(sessionId, id).catch(() => {})
    onChanged()
    setTree(await delegationsApi.tree(sessionId).catch(() => tree))
  }

  if (!tree) return <div className="text-zinc-500">{t("delegation.tree.loading")}</div>
  const s = tree.summary
  return (
    <div className="max-h-80 overflow-y-auto space-y-1">
      <div className={s.risky_commands > 0 ? "text-rose-300" : "text-zinc-300"}>
        {t("delegation.tree.summary", { active: s.active, total: s.total, cost: usd(s.cost_usd_active_chains),
          risky: s.risky_commands })}
      </div>
      {tree.nodes.filter((n) => n.status === "running" || n.children.some((c) => c.status === "running"))
        .map((n) => <TreeNodeView key={n.id} node={n} onCancel={cancel} />)}
      {tree.nodes.filter((n) => n.status !== "running" && !n.children.some((c) => c.status === "running"))
        .slice(0, 5).map((n) => <TreeNodeView key={n.id} node={n} onCancel={cancel} />)}
    </div>
  )
}
