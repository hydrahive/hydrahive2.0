import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { pluginsApi } from "./api"
import type { HubPlugin, InstalledPlugin } from "./types"

export function usePlugins() {
  const { t } = useTranslation("plugins")
  const [hub, setHub] = useState<HubPlugin[] | null>(null)
  const [installed, setInstalled] = useState<InstalledPlugin[]>([])
  const [hubError, setHubError] = useState<string | null>(null)
  const [busyName, setBusyName] = useState<string | null>(null)
  const [restartHint, setRestartHint] = useState<string | null>(null)

  async function loadInstalled() {
    try { setInstalled(await pluginsApi.installed()) }
    catch (e) { setInstalled([]); console.error(e) }
  }

  async function loadHub() {
    setHubError(null)
    try {
      const idx = await pluginsApi.hub()
      setHub(idx.plugins)
    } catch (e) {
      setHub([]); setHubError(e instanceof Error ? e.message : String(e))
    }
  }

  useEffect(() => { loadInstalled(); loadHub() }, [])

  async function handleInstall(name: string) {
    setBusyName(name)
    try {
      const r = await pluginsApi.install(name)
      if (r.restart_recommended) setRestartHint(t("restart_hint"))
      else setRestartHint(null)
      await loadInstalled()
    } catch (e) { alert(e instanceof Error ? e.message : String(e)) }
    finally { setBusyName(null) }
  }

  async function handleUninstall(name: string) {
    if (!confirm(t("uninstall_confirm", { name }))) return
    setBusyName(name)
    try {
      const r = await pluginsApi.uninstall(name)
      if (r.restart_recommended) setRestartHint(t("restart_hint"))
      await loadInstalled()
    } catch (e) { alert(e instanceof Error ? e.message : String(e)) }
    finally { setBusyName(null) }
  }

  async function handleUpdate(name: string) {
    setBusyName(name)
    try {
      const r = await pluginsApi.update(name)
      if (r.restart_recommended) setRestartHint(t("restart_hint"))
      await loadInstalled()
    } catch (e) { alert(e instanceof Error ? e.message : String(e)) }
    finally { setBusyName(null) }
  }

  return {
    hub, installed, hubError, busyName, restartHint,
    installedNames: new Set(installed.map((p) => p.name)),
    handleInstall, handleUninstall, handleUpdate,
  }
}
