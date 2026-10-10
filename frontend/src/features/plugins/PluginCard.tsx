import type { CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { Loader2, Trash2, Download, RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react"
import { rgbFor } from "@/shared/colors"
import { PluginUpdateBadge } from "./PluginUpdateBadge"
import { updateBadge, type HubAction } from "./pluginUpdates"
import type { HubPlugin, InstalledPlugin } from "./types"

const UPDATE_BTN = "bg-amber-500/15 border-amber-500/30 text-amber-300 hover:bg-amber-500/25"

interface HubCardProps {
  plugin: HubPlugin
  /** install / update / installed – aus hubCardAction (docs/specs/plugin-updates.md). */
  action: HubAction
  busy: boolean
  onInstall: () => void
  onUpdate: () => void
}

export function HubCard({ plugin, action, busy, onInstall, onUpdate }: HubCardProps) {
  const { t } = useTranslation("plugins")
  const installed = action !== "install"
  return (
    <div className="box overflow-hidden p-4 flex flex-col gap-2" style={{ "--c": rgbFor("/plugins") } as CSSProperties}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-zinc-100 truncate">{plugin.name}</h3>
          <p className="text-xs text-zinc-500 font-mono">v{plugin.version}{plugin.author && <> · {plugin.author}</>}</p>
        </div>
        {installed ? (
          <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 shrink-0">
            {t("installed_badge")}
          </span>
        ) : null}
      </div>
      <p className="text-xs text-zinc-400">{plugin.description}</p>
      {plugin.tags && plugin.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {plugin.tags.map((tag) => (
            <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-white/[6%] text-zinc-500">{tag}</span>
          ))}
        </div>
      )}
      {action === "update" ? (
        <button onClick={onUpdate} disabled={busy}
          className={`mt-1 self-start flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium disabled:opacity-50 transition-colors ${UPDATE_BTN}`}>
          {busy ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
          {t("update_available")}
        </button>
      ) : (
        <button
          onClick={onInstall}
          disabled={busy || installed}
          className="mt-1 self-start flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600/20 border border-violet-500/30 text-violet-200 text-xs font-medium hover:bg-violet-600/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {busy ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
          {installed ? t("reinstall") : t("install")}
        </button>
      )}
    </div>
  )
}

interface InstalledCardProps {
  plugin: InstalledPlugin
  busy: boolean
  onUpdate: () => void
  onUninstall: () => void
}

export function InstalledCard({ plugin, busy, onUpdate, onUninstall }: InstalledCardProps) {
  const { t } = useTranslation("plugins")
  const hasUpdate = updateBadge(plugin)?.kind === "update"
  return (
    <div className="box overflow-hidden p-4 flex flex-col gap-2" style={{ "--c": rgbFor("/plugins") } as CSSProperties}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-zinc-100 truncate">{plugin.name}</h3>
          <p className="text-xs text-zinc-500 font-mono">{plugin.version ? `v${plugin.version}` : "—"}</p>
        </div>
        {plugin.loaded ? (
          <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 shrink-0">
            <CheckCircle2 size={11} /> {t("loaded")}
          </span>
        ) : (
          <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-rose-500/15 border border-rose-500/30 text-rose-300 shrink-0">
            <AlertTriangle size={11} /> {t("not_loaded")}
          </span>
        )}
      </div>
      <PluginUpdateBadge plugin={plugin} />
      {plugin.description && <p className="text-xs text-zinc-400">{plugin.description}</p>}
      {plugin.error && (
        <p className="text-xs text-rose-300/80 font-mono break-all">{plugin.error}</p>
      )}
      {plugin.tools.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {plugin.tools.map((toolName) => (
            <span key={toolName} className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 border border-violet-500/20 text-violet-300 font-mono">
              {toolName}
            </span>
          ))}
        </div>
      )}
      <div className="flex gap-2 mt-1">
        <button
          onClick={onUpdate}
          disabled={busy}
          className={"flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium disabled:opacity-50 transition-colors " +
            (hasUpdate ? UPDATE_BTN : "bg-white/[5%] border-white/[8%] text-zinc-300 hover:bg-white/[8%]")}
        >
          {busy ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
          {hasUpdate ? t("update_available") : t("update")}
        </button>
        <button
          onClick={onUninstall}
          disabled={busy}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs font-medium hover:bg-rose-500/20 disabled:opacity-50 transition-colors"
        >
          <Trash2 size={12} />
          {t("uninstall")}
        </button>
      </div>
    </div>
  )
}
