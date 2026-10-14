import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { archiveApi, type ArchiveRemote, type RemoteForm, type RemoteTestResult } from "./api"

const EMPTY: RemoteForm = { host: "", share: "", subdir: "", user: "", password: "" }

/** Zustand + Aktionen für den Bereich „Externer Server“ (Etappe 3). Das Formular startet mit den gespeicherten
 *  Werten, das Passwort bleibt leer (leer speichern = altes behalten). */
export function useRemote(remote: ArchiveRemote | undefined, reload: () => Promise<void>) {
  const { t } = useTranslation("archive")
  const [form, setForm] = useState<RemoteForm>(EMPTY)
  const [loadedFor, setLoadedFor] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<RemoteTestResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const key = remote ? `${remote.host}|${remote.share}|${remote.subdir}|${remote.user}` : null
  useEffect(() => {
    if (!remote || key === loadedFor) return
    const sync = setTimeout(() => {
      setForm({ host: remote.host, share: remote.share, subdir: remote.subdir, user: remote.user, password: "" })
      setLoadedFor(key)
    }, 0)
    return () => clearTimeout(sync)
  }, [remote, key, loadedFor])

  async function run(fn: () => Promise<unknown>) {
    setBusy(true); setError(null)
    try { await fn(); await reload() }
    catch (err) { setError(err instanceof Error ? err.message : t("remote.error.unexpected")) }
    finally { setBusy(false) }
  }

  return {
    form, testResult, busy, error,
    onForm: setForm,
    onSave: () => void run(async () => { await archiveApi.remoteSave(form); setForm({ ...form, password: "" }); setTestResult(null) }),
    onTest: () => void run(async () => setTestResult(await archiveApi.remoteTest())),
    onActive: (active: boolean) => void run(() => archiveApi.remoteActive(active)),
    onSync: () => void run(() => archiveApi.remoteSync()),
  }
}
