import { Brain } from "lucide-react"
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
      <div className="rounded-lg border border-white/[6%] bg-white/[3%] px-3 py-2.5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Brain size={14} className="text-violet-400 shrink-0" />
          <div>
            <p className="text-xs font-medium text-zinc-200">Langzeitgedächtnis</p>
            <p className="text-[10px] text-zinc-500">datamining_search · datamining_semantic · datamining_today</p>
          </div>
        </div>
        <button
          onClick={() => onChange({ longterm_memory: !draft.longterm_memory })}
          className={`relative w-9 h-5 rounded-full transition-colors ${
            draft.longterm_memory ? "bg-violet-600" : "bg-white/10"
          }`}
        >
          <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
            draft.longterm_memory ? "translate-x-4" : "translate-x-0"
          }`} />
        </button>
      </div>

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
