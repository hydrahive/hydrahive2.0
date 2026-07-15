import { useState } from "react"
import { useTranslation } from "react-i18next"
import { RotateCw } from "lucide-react"
import { usePlugins } from "@/features/plugins/usePlugins"
import { RestartModal } from "@/shared/RestartModal"
import { useRestart } from "@/shared/useRestart"
import { CockpitButton } from "../CockpitButton"
import { AdminOverlay } from "./AdminOverlay"
import { HubCockpitCard, InstalledCockpitCard } from "./PluginCockpitCards"

type Tab = "hub" | "installed"

export function PluginsOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("plugins")
  const { t: tNav } = useTranslation("nav")
  const restart = useRestart()
  const [tab, setTab] = useState<Tab>("hub")
  const { hub, installed, hubError, busyName, restartHint, installedNames,
          handleInstall, handleUninstall, handleUpdate } = usePlugins()

  return (
    <AdminOverlay
      eyebrow="Admin"
      title={t("title")}
      onClose={onClose}
      maxWidthClass="max-w-4xl"
      headerActions={
        <CockpitButton onClick={restart.open}>
          <RotateCw size={12} className="mr-1 inline" />{tNav("restart.button")}
        </CockpitButton>
      }
    >
      <div className="space-y-4">
        <div className="flex gap-2 border-b border-[#2a364b]">
          {(["hub", "installed"] as Tab[]).map((tid) => (
            <button key={tid} onClick={() => setTab(tid)}
              className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                tab === tid ? "border-violet-500 text-violet-300" : "border-transparent text-[#8d9ab0] hover:text-[#e8eef8]"
              }`}>
              {tid === "hub" ? t("tab_hub") : `${t("tab_installed")} (${installed.length})`}
            </button>
          ))}
        </div>

        {restartHint && (
          <div className="flex items-center justify-between gap-3 rounded-[4px] border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
            <span>{restartHint}</span>
            <button onClick={restart.open}
              className="flex shrink-0 items-center gap-1.5 rounded-[4px] border border-amber-500/40 bg-amber-500/20 px-2.5 py-1 text-[11px] font-medium text-amber-100 transition-colors hover:bg-amber-500/30">
              <RotateCw size={11} /> {tNav("restart.now")}
            </button>
          </div>
        )}

        {tab === "hub" && (
          <div>
            {hubError && <div className="mb-4 rounded-[4px] border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">{hubError}</div>}
            {hub === null ? (
              <p className="text-sm text-[#8d9ab0]">{t("loading")}</p>
            ) : hub.length === 0 ? (
              <p className="text-sm text-[#8d9ab0]">{t("hub_empty")}</p>
            ) : (
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {hub.map((p) => (
                  <HubCockpitCard key={p.name} plugin={p} installed={installedNames.has(p.name)}
                    busy={busyName === p.name} onInstall={() => handleInstall(p.name)} />
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "installed" && (
          <div>
            {installed.length === 0 ? (
              <p className="text-sm text-[#8d9ab0]">{t("installed_empty")}</p>
            ) : (
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {installed.map((p) => (
                  <InstalledCockpitCard key={p.name} plugin={p} busy={busyName === p.name}
                    onUpdate={() => handleUpdate(p.name)} onUninstall={() => handleUninstall(p.name)} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {restart.state !== "idle" && (
        <RestartModal state={restart.state} errorMessage={restart.error} onConfirm={restart.confirm} onClose={restart.close} />
      )}
    </AdminOverlay>
  )
}
