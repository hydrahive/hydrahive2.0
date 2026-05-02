import { Crown, Trash2, User, Wrench } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { Agent } from "./types"

const TYPE_ICON = { master: Crown, project: User, specialist: Wrench }

interface Props {
  agent: Agent
  draftName: string
  draftStatus: Agent["status"]
  onNameChange: (name: string) => void
  onStatusChange: (status: Agent["status"]) => void
  onDelete: () => void
}

export function AgentFormHeader({ agent, draftName, draftStatus, onNameChange, onStatusChange, onDelete }: Props) {
  const { t: tCommon } = useTranslation("common")
  const Icon = TYPE_ICON[agent.type] ?? Wrench
  return (
    <div className="px-5 py-2.5 border-b border-white/[6%] flex items-center gap-3 bg-zinc-950/80 backdrop-blur">
      <Icon size={16} className="text-violet-300 flex-shrink-0" />
      <input
        value={draftName}
        onChange={(e) => onNameChange(e.target.value)}
        className="flex-1 bg-transparent text-base font-bold text-white focus:outline-none min-w-0"
      />
      <select
        value={draftStatus}
        onChange={(e) => onStatusChange(e.target.value as Agent["status"])}
        className="px-2 py-1 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-300"
      >
        <option value="active">{tCommon("status.active")}</option>
        <option value="disabled">{tCommon("status.disabled")}</option>
      </select>
      <button
        onClick={onDelete}
        className="p-1.5 rounded-md text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
        title={tCommon("actions.delete")}
      >
        <Trash2 size={14} />
      </button>
    </div>
  )
}
