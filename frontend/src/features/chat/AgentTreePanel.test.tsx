import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { ToolLine, TreeNodeView } from "./AgentTreePanel"
import type { TreeNode, TreeTool } from "./delegationsApi"

const noop = () => {}
const tool = (p: Partial<TreeTool>): TreeTool =>
  ({ tool: "shell_exec", label: "pytest -q", status: "success", at: "2026-11-20T20:34:18Z", risky: false, blocked: false, ...p })

const node = (p: Partial<TreeNode>): TreeNode => ({
  id: "d1", target_agent_id: "a", target_name: "backend-engineer", task: "Etappe B", status: "running", depth: 2,
  created_at: "2026-11-20T20:20:00Z", deadline_at: "2026-11-20T21:20:00Z", finished_at: null, delivered: false,
  target_session_id: "s", rounds: 3, current_tool: null,
  cost: { calls: 96, cost_usd: 0.69, output_tokens: 1000, model: "claude-sonnet-5" },
  recent_tools: [], flagged_tools: [], tool_count: 96, children: [], ...p,
})

describe("AgentTreePanel", () => {
  it("riskante Befehle sind rot markiert, harmlose nicht", () => {
    expect(renderToStaticMarkup(<ToolLine tool={tool({ risky: true, label: "ssh 192.168.178.197 sudo" })} />))
      .toContain("text-rose-300")
    expect(renderToStaticMarkup(<ToolLine tool={tool({})} />)).not.toContain("text-rose-300")
  })

  it("laufender Knoten zeigt Kosten, Modell, Warnzähler und Unteragenten", () => {
    const child = node({ id: "d2", target_name: "haushaltsbuch-frontend", status: "done" })
    const html = renderToStaticMarkup(
      <TreeNodeView node={node({ flagged_tools: [tool({ risky: true, label: "ssh host" })], children: [child] })}
        onCancel={noop} />,
    )
    expect(html).toContain("backend-engineer")
    expect(html).toContain("0.69 $")
    expect(html).toContain("claude-sonnet-5")
    expect(html).toContain("⚠ 1")
    expect(html).toContain("ssh host")
    expect(html).toContain("haushaltsbuch-frontend")   // laufende Knoten sind aufgeklappt → Kinder sichtbar
  })
})
