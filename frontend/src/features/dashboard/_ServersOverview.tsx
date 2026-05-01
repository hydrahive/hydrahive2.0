import { Box, HardDrive } from "lucide-react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"
import type { DashboardServer } from "./api"

interface Props {
  servers: DashboardServer[]
}

export function ServersOverview({ servers }: Props) {
  const { t } = useTranslation("dashboard")
  return (
    <div className="rounded-xl border border-white/[8%] bg-white/[3%] p-4">
      <h3 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500 mb-2">
        {t("sections.servers")}
      </h3>
      {servers.length === 0 ? (
        <p className="text-xs text-zinc-500 py-4 text-center">{t("sections.servers_empty")}</p>
      ) : (
        <div className="space-y-1">
          {servers.slice(0, 8).map((s) => {
            const Icon = s.kind === "vm" ? HardDrive : Box
            const tone = s.actual_state === "running" ? "emerald" :
                         s.actual_state === "error" ? "rose" : "zinc"
            const dot: Record<string, string> = {
              emerald: "bg-emerald-400 shadow-[0_0_5px_rgba(52,211,153,0.55)]",
              rose: "bg-rose-400",
              zinc: "bg-zinc-600",
            }
            return (
              <Link key={`${s.kind}:${s.id}`}
                to={s.kind === "vm" ? `/vms/${s.id}` : `/containers/${s.id}`}
                className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-white/[4%] transition-colors">
                <Icon size={12} className="text-violet-300 flex-shrink-0" />
                <span className="text-xs text-zinc-200 flex-1 truncate">{s.name}</span>
                <span className="text-[10px] text-zinc-600 flex-shrink-0">{s.kind.toUpperCase()}</span>
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dot[tone]}`} />
              </Link>
            )
          })}
          {servers.length > 8 && (
            <p className="text-[10px] text-zinc-600 pt-1 text-center">+ {servers.length - 8}</p>
          )}
        </div>
      )}
    </div>
  )
}
