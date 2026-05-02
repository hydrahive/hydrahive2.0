import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Puzzle, RotateCw } from "lucide-react"
import { HubCard, InstalledCard } from "./PluginCard"
import { usePlugins } from "./usePlugins"
import { RestartModal } from "@/shared/RestartModal"
import { useRestart } from "@/shared/useRestart"

type Tab = "hub" | "installed"

export function PluginsPage() {
  const { t } = useTranslation("plugins")
  const { t: tNav } = useTranslation("nav")
  const restart = useRestart()
  const [tab, setTab] = useState<Tab>("hub")
  const { hub, installed, hubError, busyName, restartHint, installedNames,
          handleInstall, handleUninstall, handleUpdate } = usePlugins()

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Puzzle className="text-violet-400" size={20} />
          <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
        </div>
        <button onClick={restart.open}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-300 text-xs font-medium hover:bg-white/[8%] transition-colors">
          <RotateCw size={12} /> {tNav("restart.button")}
        </button>
      </div>

      <div className="flex gap-2 border-b border-white/[6%]">
        {(["hub", "installed"] as Tab[]).map((t_id) => (
          <button key={t_id} onClick={() => setTab(t_id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t_id ? "border-violet-500 text-violet-300" : "border-transparent text-zinc-500 hover:text-zinc-300"
            }`}>
            {t_id === "hub" ? t("tab_hub") : `${t("tab_installed")} (${installed.length})`}
          </button>
        ))}
      </div>

      {restartHint && (
        <div className="px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs flex items-center justify-between gap-3">
          <span>{restartHint}</span>
          <button onClick={restart.open}
            className="shrink-0 flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-100 text-[11px] font-medium transition-colors">
            <RotateCw size={11} /> {tNav("restart.now")}
          </button>
        </div>
      )}

      {tab === "hub" && (
        <div>
          {hubError && (
            <div className="px-3 py-2 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-200 text-xs mb-4">{hubError}</div>
          )}
          {hub === null ? (
            <p className="text-zinc-500 text-sm">{t("loading")}</p>
          ) : hub.length === 0 ? (
            <p className="text-zinc-500 text-sm">{t("hub_empty")}</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {hub.map((p) => (
                <HubCard key={p.name} plugin={p} installed={installedNames.has(p.name)}
                  busy={busyName === p.name} onInstall={() => handleInstall(p.name)} />
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "installed" && (
        <div>
          {installed.length === 0 ? (
            <p className="text-zinc-500 text-sm">{t("installed_empty")}</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {installed.map((p) => (
                <InstalledCard key={p.name} plugin={p} busy={busyName === p.name}
                  onUpdate={() => handleUpdate(p.name)} onUninstall={() => handleUninstall(p.name)} />
              ))}
            </div>
          )}
        </div>
      )}

      {restart.state !== "idle" && (
        <RestartModal state={restart.state} errorMessage={restart.error}
          onConfirm={restart.confirm} onClose={restart.close} />
      )}
    </div>
  )
}
