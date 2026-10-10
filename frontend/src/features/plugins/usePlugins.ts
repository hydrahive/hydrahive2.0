import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { pluginsApi } from "./api"
import { hubCardAction, outdatedNames } from "./pluginUpdates"
import type { HubPlugin, InstalledPlugin } from "./types"

export function usePlugins() {
  const { t } = useTranslation("plugins")
  const [hub, setHub] = useState<HubPlugin[] | null>(null)
  const [installed, setInstalled] = useState<InstalledPlugin[]>([])
  const [hubError, setHubError] = useState<string | null>(null)
  const [busyName, setBusyName] = useState<string | null>(null)
  const [restartHint, setRestartHint] = useState<string | null>(null)
  const [batch, setBatch] = useState<{ done: number; total: number } | null>(null)

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

  // Erst Hub auffrischen (git), DANN die Liste laden – sonst vergleicht die Update-Erkennung mit altem Cache.
  // Laden beim Öffnen = Abgleich mit dem Server (wie ModulesOverlay).
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void loadInstalled(); void loadHub().then(loadInstalled) }, [])

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

  const outdated = outdatedNames(installed)

  /** „Alle updaten“: nacheinander, dann EIN Neustart-Hinweis (wie bei den Modulen). */
  async function handleUpdateAll() {
    if (outdated.length === 0 || batch) return
    const names = [...outdated]
    setBatch({ done: 0, total: names.length })
    const failed: string[] = []
    for (let i = 0; i < names.length; i++) {
      setBusyName(names[i])
      try { await pluginsApi.update(names[i]) } catch { failed.push(names[i]) }
      setBatch({ done: i + 1, total: names.length })
    }
    setBusyName(null); setBatch(null)
    setRestartHint(t("restart_hint"))
    if (failed.length) alert(failed.join(", "))
    await loadInstalled()
  }

  const byName = new Map(installed.map((p) => [p.name, p]))
  return {
    hub, installed, hubError, busyName, restartHint, batch, outdated,
    installedNames: new Set(byName.keys()),
    hubAction: (name: string) => hubCardAction(name, byName),
    handleInstall, handleUninstall, handleUpdate, handleUpdateAll,
  }
}
