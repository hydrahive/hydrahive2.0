import { useTranslation } from "react-i18next"
import { Loader2, Trash2, Download, RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react"
import type { HubPlugin, InstalledPlugin } from "./types"

interface HubCardProps {
  plugin: HubPlugin
  installed: boolean
  busy: boolean
  onInstall: () => void
}

export function HubCard({ plugin, installed, busy, onInstall }: HubCardProps) {
  const { t } = useTranslation("plugins")
  return (
    <div className="rounded-xl border border-white/[6%] bg-zinc-950/50 p-4 flex flex-col gap-2">
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
      <button
        onClick={onInstall}
        disabled={busy || installed}
        className="mt-1 self-start flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600/20 border border-violet-500/30 text-violet-200 text-xs font-medium hover:bg-violet-600/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {busy ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
        {installed ? t("reinstall") : t("install")}
      </button>
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
  return (
    <div className="rounded-xl border border-white/[6%] bg-zinc-950/50 p-4 flex flex-col gap-2">
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
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-300 text-xs font-medium hover:bg-white/[8%] disabled:opacity-50 transition-colors"
        >
          {busy ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
          {t("update")}
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
