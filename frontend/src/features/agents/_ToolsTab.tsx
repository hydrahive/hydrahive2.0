import { useTranslation } from "react-i18next"
import { McpSelector } from "./McpSelector"
import { ToolsSelector } from "./ToolsSelector"
import type { Agent, ToolMeta } from "./types"
import type { McpServerBrief } from "./api"

interface Props {
  draft: Agent
  tools: ToolMeta[]
  mcpServers: McpServerBrief[]
  onChange: (patch: Partial<Agent>) => void
}

export function ToolsTab({ draft, tools, mcpServers, onChange }: Props) {
  const { t } = useTranslation("agents")
  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <p className="text-[10px] font-medium text-zinc-500">
          {t("fields.tools_count", { selected: draft.tools.length, total: tools.length })}
        </p>
        <ToolsSelector
          available={tools}
          selected={draft.tools}
          onChange={(v) => onChange({ tools: v })}
        />
      </div>
      <div className="space-y-1">
        <p className="text-[10px] font-medium text-zinc-500">
          {t("fields.mcp_count", { selected: draft.mcp_servers.length, total: mcpServers.length })}
        </p>
        <McpSelector
          available={mcpServers}
          selected={draft.mcp_servers}
          onChange={(v) => onChange({ mcp_servers: v })}
        />
      </div>
    </div>
  )
}
