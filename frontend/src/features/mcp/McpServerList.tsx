import { Plug, PlugZap, Plus, Server, Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import { HelpButton } from "@/i18n/HelpButton"
import type { McpServer } from "./types"

interface Props {
  servers: McpServer[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onQuickAdd: () => void
}

export function McpServerList({ servers, activeId, onSelect, onNew, onQuickAdd }: Props) {
  const { t } = useTranslation("mcp")
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-3 border-b border-white/[6%]">
        <p className="text-xs font-semibold uppercase tracking-widest text-zinc-500">{t("list_title")}</p>
        <div className="flex items-center gap-1">
          <HelpButton topic="mcp" />
          <button
            onClick={onQuickAdd}
            title={t("actions.template_tooltip")}
            className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs text-violet-300 hover:text-violet-200 hover:bg-violet-500/10 transition-colors"
          >
            <Sparkles size={12} /> {t("actions.template_button")}
          </button>
          <button
            onClick={onNew}
            className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs text-zinc-300 hover:text-zinc-100 hover:bg-white/5 transition-colors"
          >
            <Plus size={12} /> {t("actions.new_button")}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {servers.length === 0 && (
          <p className="text-xs text-zinc-600 text-center py-6">{t("no_servers")}</p>
        )}
        {servers.map((s) => {
          const active = s.id === activeId
          const dim = !s.enabled
          const statusCls = s.connected
            ? "bg-emerald-500/[8%] border-emerald-500/25 text-emerald-300"
            : "bg-zinc-500/[8%] border-zinc-500/20 text-zinc-500"
          const StatusIcon = s.connected ? PlugZap : Plug
          return (
            <div
              key={s.id}
              className={`group flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all ${
                active
                  ? "bg-gradient-to-r from-indigo-600/20 to-violet-600/10 border-l-2 border-violet-500"
                  : "hover:bg-white/[3%] border-l-2 border-transparent"
              } ${dim ? "opacity-50" : ""}`}
              onClick={() => onSelect(s.id)}
            >
              <Server size={14} className={active ? "text-violet-300" : "text-zinc-500"} />
              <div className="flex-1 min-w-0">
                <p className={`text-sm truncate ${active ? "text-white" : "text-zinc-300"}`}>
                  {s.name}
                </p>
                <p className="text-[10px] text-zinc-600 mt-0.5 truncate font-mono">
                  {s.transport} · {s.id}
                </p>
              </div>
              <span className={`flex items-center gap-1 px-1.5 py-0.5 rounded-full border text-[10px] flex-shrink-0 ${statusCls}`}>
                <StatusIcon size={9} />
                {s.connected ? "live" : "off"}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
