import { Server } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { McpServerBrief } from "./api"

interface Props {
  available: McpServerBrief[]
  selected: string[]
  onChange: (next: string[]) => void
}

export function McpSelector({ available, selected, onChange }: Props) {
  const { t } = useTranslation("agents")
  const { t: tCommon } = useTranslation("common")
  if (available.length === 0) {
    return <p className="text-xs text-zinc-600">{t("errors.no_servers_yet")}</p>
  }
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-1">
      {available.map((s) => {
        const checked = selected.includes(s.id)
        return (
          <button
            key={s.id}
            type="button"
            onClick={() => {
              const next = checked ? selected.filter((id) => id !== s.id) : [...selected, s.id]
              onChange(next)
            }}
            title={`${s.id} · ${s.connected ? tCommon("status.connected") : tCommon("status.disconnected")}`}
            className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-left transition-all ${
              checked
                ? "border-violet-500/40 bg-violet-500/[8%]"
                : "border-white/[6%] bg-white/[2%] hover:bg-white/[4%]"
            }`}
          >
            <Server size={11} className={checked ? "text-violet-300" : "text-zinc-500"} />
            <p className="text-[11px] text-zinc-200 truncate flex-1">{s.name}</p>
            <span
              className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                s.connected ? "bg-emerald-400" : "bg-zinc-600"
              }`}
            />
          </button>
        )
      })}
    </div>
  )
}
