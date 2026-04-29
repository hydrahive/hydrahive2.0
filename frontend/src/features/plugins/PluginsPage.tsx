import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Puzzle } from "lucide-react"
import { pluginsApi } from "./api"
import type { HubPlugin, InstalledPlugin } from "./types"
import { HubCard, InstalledCard } from "./PluginCard"

type Tab = "hub" | "installed"

export function PluginsPage() {
  const { t } = useTranslation("plugins")
  const [tab, setTab] = useState<Tab>("hub")
  const [hub, setHub] = useState<HubPlugin[] | null>(null)
  const [installed, setInstalled] = useState<InstalledPlugin[]>([])
  const [hubError, setHubError] = useState<string | null>(null)
  const [busyName, setBusyName] = useState<string | null>(null)
  const [restartHint, setRestartHint] = useState<string | null>(null)

  async function loadInstalled() {
    try {
      setInstalled(await pluginsApi.installed())
    } catch (e) {
      setInstalled([])
      console.error(e)
    }
  }

  async function loadHub() {
    setHubError(null)
    try {
      const idx = await pluginsApi.hub()
      setHub(idx.plugins)
    } catch (e) {
      setHub([])
      setHubError(e instanceof Error ? e.message : String(e))
    }
  }

  useEffect(() => {
    loadInstalled()
    loadHub()
  }, [])

  const installedNames = new Set(installed.map((p) => p.name))

  async function handleInstall(name: string) {
    setBusyName(name)
    try {
      const r = await pluginsApi.install(name)
      if (r.restart_recommended) setRestartHint(t("restart_hint"))
      else setRestartHint(null)
      await loadInstalled()
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e))
    } finally {
      setBusyName(null)
    }
  }

  async function handleUninstall(name: string) {
    if (!confirm(t("uninstall_confirm", { name }))) return
    setBusyName(name)
    try {
      const r = await pluginsApi.uninstall(name)
      if (r.restart_recommended) setRestartHint(t("restart_hint"))
      await loadInstalled()
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e))
    } finally {
      setBusyName(null)
    }
  }

  async function handleUpdate(name: string) {
    setBusyName(name)
    try {
      const r = await pluginsApi.update(name)
      if (r.restart_recommended) setRestartHint(t("restart_hint"))
      await loadInstalled()
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e))
    } finally {
      setBusyName(null)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Puzzle className="text-violet-400" size={20} />
        <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
      </div>

      <div className="flex gap-2 border-b border-white/[6%]">
        <button
          onClick={() => setTab("hub")}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            tab === "hub"
              ? "border-violet-500 text-violet-300"
              : "border-transparent text-zinc-500 hover:text-zinc-300"
          }`}
        >
          {t("tab_hub")}
        </button>
        <button
          onClick={() => setTab("installed")}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            tab === "installed"
              ? "border-violet-500 text-violet-300"
              : "border-transparent text-zinc-500 hover:text-zinc-300"
          }`}
        >
          {t("tab_installed")} ({installed.length})
        </button>
      </div>

      {restartHint && (
        <div className="px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs">
          {restartHint}
        </div>
      )}

      {tab === "hub" && (
        <div>
          {hubError && (
            <div className="px-3 py-2 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-200 text-xs mb-4">
              {hubError}
            </div>
          )}
          {hub === null ? (
            <p className="text-zinc-500 text-sm">{t("loading")}</p>
          ) : hub.length === 0 ? (
            <p className="text-zinc-500 text-sm">{t("hub_empty")}</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {hub.map((p) => (
                <HubCard
                  key={p.name}
                  plugin={p}
                  installed={installedNames.has(p.name)}
                  busy={busyName === p.name}
                  onInstall={() => handleInstall(p.name)}
                />
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
                <InstalledCard
                  key={p.name}
                  plugin={p}
                  busy={busyName === p.name}
                  onUpdate={() => handleUpdate(p.name)}
                  onUninstall={() => handleUninstall(p.name)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
