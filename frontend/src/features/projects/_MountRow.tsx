import type { CSSProperties } from "react"
import { FolderInput, Loader2, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { rgbFor } from "@/shared/colors"
import type { SmbMount } from "./types"

interface Props { mount: SmbMount; busy: boolean; onUnassign: () => void }

export function MountRow({ mount, busy, onUnassign }: Props) {
  const { t } = useTranslation("projects")
  const tone = mount.mount_state === "mounted" ? "emerald" :
               mount.mount_state === "error" ? "rose" : "zinc"
  const tonePill: Record<string, string> = {
    emerald: "bg-emerald-500/[8%] border-emerald-500/20 text-emerald-300",
    rose: "bg-rose-500/[8%] border-rose-500/20 text-rose-300",
    zinc: "bg-zinc-500/[8%] border-zinc-500/20 text-zinc-400",
  }
  const unc = `//${mount.host}/${mount.share}${mount.subpath ? "/" + mount.subpath : ""}`

  return (
    <div className="flex items-center gap-2 px-3 py-2 box overflow-hidden" style={{ "--c": rgbFor("/projects") } as CSSProperties}>
      <FolderInput size={14} className="text-violet-300 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-zinc-200 truncate">
          {mount.name}
          {mount.read_only && <span className="ml-1.5 text-[10px] text-amber-400/80">RO</span>}
        </p>
        <p className="text-[10px] text-zinc-600 truncate font-mono">{unc}</p>
        {mount.mount_state === "error" && mount.last_error_code && (
          <p className="text-[10px] text-rose-400/80 truncate">{mount.last_error_code}</p>
        )}
      </div>
      <span className={`px-2 py-0.5 rounded-full border text-[10px] ${tonePill[tone]}`}>
        {mount.mount_state}
      </span>
      <button onClick={onUnassign} disabled={busy}
        className="p-1.5 rounded text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 disabled:opacity-30"
        title={t("mounts.unassign")}>
        {busy ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
      </button>
    </div>
  )
}
