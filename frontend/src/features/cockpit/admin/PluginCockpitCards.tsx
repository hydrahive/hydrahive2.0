import { useTranslation } from "react-i18next"
import { AlertTriangle, CheckCircle2, Download, Loader2, RefreshCw, Trash2 } from "lucide-react"
import type { HubPlugin, InstalledPlugin } from "@/features/plugins/types"

/** Hub-Plugin-Karte im Cockpit-Design (Pendant zu features/plugins/PluginCard HubCard). */
export function HubCockpitCard({ plugin, installed, busy, onInstall }: {
  plugin: HubPlugin; installed: boolean; busy: boolean; onInstall: () => void
}) {
  const { t } = useTranslation("plugins")
  return (
    <div className="flex flex-col gap-2 rounded-[6px] border border-[#2a364b] bg-[#111827] p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-[#e8eef8]">{plugin.name}</h3>
          <p className="font-mono text-xs text-[#8d9ab0]">v{plugin.version}{plugin.author && <> · {plugin.author}</>}</p>
        </div>
        {installed && (
          <span className="shrink-0 rounded border border-emerald-500/30 bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">{t("installed_badge")}</span>
        )}
      </div>
      <p className="text-xs text-[#8d9ab0]">{plugin.description}</p>
      {plugin.tags && plugin.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {plugin.tags.map((tag) => <span key={tag} className="rounded bg-white/[6%] px-1.5 py-0.5 text-[10px] text-[#8d9ab0]">{tag}</span>)}
        </div>
      )}
      <button onClick={onInstall} disabled={busy || installed}
        className="mt-1 flex items-center gap-1.5 self-start rounded-[4px] border border-violet-500/30 bg-violet-600/20 px-3 py-1.5 text-xs font-medium text-violet-200 transition-colors hover:bg-violet-600/30 disabled:cursor-not-allowed disabled:opacity-50">
        {busy ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
        {installed ? t("reinstall") : t("install")}
      </button>
    </div>
  )
}

/** Installierte-Plugin-Karte im Cockpit-Design (Pendant zu InstalledCard). */
export function InstalledCockpitCard({ plugin, busy, onUpdate, onUninstall }: {
  plugin: InstalledPlugin; busy: boolean; onUpdate: () => void; onUninstall: () => void
}) {
  const { t } = useTranslation("plugins")
  return (
    <div className="flex flex-col gap-2 rounded-[6px] border border-[#2a364b] bg-[#111827] p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-[#e8eef8]">{plugin.name}</h3>
          <p className="font-mono text-xs text-[#8d9ab0]">{plugin.version ? `v${plugin.version}` : "—"}</p>
        </div>
        {plugin.loaded ? (
          <span className="flex shrink-0 items-center gap-1 rounded border border-emerald-500/30 bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-300">
            <CheckCircle2 size={11} /> {t("loaded")}
          </span>
        ) : (
          <span className="flex shrink-0 items-center gap-1 rounded border border-rose-500/30 bg-rose-500/15 px-2 py-0.5 text-xs text-rose-300">
            <AlertTriangle size={11} /> {t("not_loaded")}
          </span>
        )}
      </div>
      {plugin.description && <p className="text-xs text-[#8d9ab0]">{plugin.description}</p>}
      {plugin.error && <p className="break-all font-mono text-xs text-rose-300/80">{plugin.error}</p>}
      {plugin.tools.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {plugin.tools.map((toolName) => (
            <span key={toolName} className="rounded border border-violet-500/20 bg-violet-500/10 px-1.5 py-0.5 font-mono text-[10px] text-violet-300">{toolName}</span>
          ))}
        </div>
      )}
      <div className="mt-1 flex gap-2">
        <button onClick={onUpdate} disabled={busy}
          className="flex items-center gap-1.5 rounded-[4px] border border-[#2a364b] bg-[#172133] px-3 py-1.5 text-xs font-medium text-[#d7deea] transition-colors hover:bg-[#1b2536] disabled:opacity-50">
          {busy ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}{t("update")}
        </button>
        <button onClick={onUninstall} disabled={busy}
          className="flex items-center gap-1.5 rounded-[4px] border border-rose-500/20 bg-rose-500/10 px-3 py-1.5 text-xs font-medium text-rose-300 transition-colors hover:bg-rose-500/20 disabled:opacity-50">
          <Trash2 size={12} />{t("uninstall")}
        </button>
      </div>
    </div>
  )
}
