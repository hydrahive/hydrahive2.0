import { Box, ExternalLink, HardDrive, Loader2, Trash2 } from "lucide-react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"
import type { ProjectServer } from "./types"

interface Props { server: ProjectServer; busy: boolean; onUnassign: () => void }

export function ServerRow({ server, busy, onUnassign }: Props) {
  const { t } = useTranslation("projects")
  const Icon = server.kind === "vm" ? HardDrive : Box
  const tone = server.actual_state === "running" ? "emerald" :
               server.actual_state === "error" ? "rose" : "zinc"
  const tonePill: Record<string, string> = {
    emerald: "bg-emerald-500/[8%] border-emerald-500/20 text-emerald-300",
    rose: "bg-rose-500/[8%] border-rose-500/20 text-rose-300",
    zinc: "bg-zinc-500/[8%] border-zinc-500/20 text-zinc-400",
  }
  const detailHref = server.kind === "vm" ? `/vms/${server.id}` : `/containers/${server.id}`

  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-white/[8%] bg-white/[2%]">
      <Icon size={14} className="text-violet-300 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-zinc-200 truncate">{server.name}</p>
        <p className="text-[10px] text-zinc-600 truncate">
          {server.kind.toUpperCase()} · {server.cpu ?? "?"} CPU · {server.ram_mb ?? "?"} MB
          {server.kind === "vm" && server.disk_gb && ` · ${server.disk_gb} GB`}
          {server.kind === "container" && server.image && ` · ${server.image}`}
        </p>
      </div>
      <span className={`px-2 py-0.5 rounded-full border text-[10px] ${tonePill[tone]}`}>
        {server.actual_state}
      </span>
      <Link to={detailHref} className="p-1.5 rounded text-zinc-500 hover:text-violet-300 hover:bg-violet-500/10"
        title={t("servers.open_detail")}>
        <ExternalLink size={12} />
      </Link>
      <button onClick={onUnassign} disabled={busy}
        className="p-1.5 rounded text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 disabled:opacity-30"
        title={t("servers.unassign")}>
        {busy ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
      </button>
    </div>
  )
}
