import { Loader2, Plug, PlugZap, Save, Server, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { McpServer } from "./types"

interface Props {
  server: McpServer
  draftName: string
  saving: boolean
  busy: boolean
  onNameChange: (name: string) => void
  onSave: () => void
  onToggleConnect: () => void
  onDelete: () => void
}

export function McpServerFormHeader({ server, draftName, saving, busy, onNameChange, onSave, onToggleConnect, onDelete }: Props) {
  const { t } = useTranslation("mcp")
  const { t: tCommon } = useTranslation("common")
  return (
    <div className="px-6 py-4 border-b border-white/[6%] flex items-center gap-3">
      <Server size={18} className="text-violet-300 flex-shrink-0" />
      <input value={draftName} onChange={(e) => onNameChange(e.target.value)}
        className="flex-1 bg-transparent text-lg font-bold text-white focus:outline-none" />
      <button onClick={onToggleConnect} disabled={busy || !server.enabled}
        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
          server.connected
            ? "bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border border-emerald-500/30"
            : "bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-white/[8%]"
        } disabled:opacity-30`}>
        {busy ? <Loader2 size={14} className="animate-spin" /> :
          (server.connected ? <PlugZap size={14} /> : <Plug size={14} />)}
        {server.connected ? t("actions.connected") : t("actions.connect")}
      </button>
      <button onClick={onSave} disabled={saving}
        className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-30 shadow-md shadow-violet-900/20">
        {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
        {tCommon("actions.save")}
      </button>
      <button onClick={onDelete} className="p-2 rounded-lg text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors">
        <Trash2 size={15} />
      </button>
    </div>
  )
}
