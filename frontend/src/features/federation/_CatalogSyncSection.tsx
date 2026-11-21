import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { RefreshCw } from "lucide-react"
import { catalogApi } from "./api"
import type { CatalogSettings } from "./types"
import { usersApi } from "@/features/users/api"
import { projectsApi } from "@/features/projects/api"
import { CatalogSyncForm } from "./_CatalogSyncForm"
import { draftToPatch, toDraft, type CatalogDraft } from "./_catalogSync"

interface Props {
  /** Ändert sich, wenn im Reiter ein Hub-/Annehmen-Schalter umgelegt wurde → Hub-Anzeige neu laden. */
  reloadKey: number
}

// Föderations-Katalog (docs/specs/federation-catalog.md §Oberfläche, „Auf dem Client“):
// Abschnitt „Katalog-Sync“: Einstellungen, Status und „Jetzt abgleichen“ (Etappe 3).
export function CatalogSyncSection({ reloadKey }: Props) {
  const { t } = useTranslation("federation")
  const [settings, setSettings] = useState<CatalogSettings | null>(null)
  const [draft, setDraft] = useState<CatalogDraft | null>(null)
  const [users, setUsers] = useState<string[]>([])
  const [projects, setProjects] = useState<{ id: string; name: string }[]>([])
  const [error, setError] = useState("")
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState("")

  // Bei jedem reloadKey neu laden. Der Entwurf bleibt, wenn schon einer existiert (ungespeicherte Eingaben).
  useEffect(() => {
    let cancelled = false
    catalogApi.getSettings()
      .then(s => {
        if (cancelled) return
        setSettings(s)
        setDraft(prev => prev ?? toDraft(s))
        setError("")
      })
      .catch(e => { if (!cancelled) setError(e instanceof Error ? e.message : t("catalog.load_error")) })
    return () => { cancelled = true }
  }, [t, reloadKey])

  useEffect(() => {
    usersApi.list().then(list => setUsers(list.map(u => u.username).sort())).catch(() => {})
    projectsApi.list()
      .then(list => setProjects(list.map(p => ({ id: p.id, name: p.name })).sort((a, b) => a.name.localeCompare(b.name))))
      .catch(() => {})
  }, [])

  async function save() {
    if (!draft) return
    const patch = draftToPatch(draft)
    if (!patch) return
    setSaving(true)
    setError("")
    setSaved(false)
    try {
      const s = await catalogApi.saveSettings(patch)
      setSettings(s)
      setDraft(toDraft(s))
      setSaved(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : t("peers.error"))
    } finally {
      setSaving(false)
    }
  }

  async function syncNow() {
    setSyncing(true)
    setSyncResult("")
    setError("")
    try {
      const r = await catalogApi.syncNow()
      setSettings(r.settings)
      setSyncResult(r.result)
    } catch (e) {
      setError(e instanceof Error ? e.message : t("peers.error"))
    } finally {
      setSyncing(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <RefreshCw size={15} className="text-violet-400" />
        <span className="text-sm font-medium text-zinc-200">{t("catalog.sync_title")}</span>
        <span className="text-xs text-zinc-500 ml-1">{t("catalog.sync_subtitle")}</span>
      </div>
      {settings && draft ? (
        <CatalogSyncForm
          settings={settings}
          draft={draft}
          users={users}
          projects={projects}
          saving={saving}
          saved={saved}
          error={error}
          onChange={next => { setDraft(next); setSaved(false) }}
          onSave={save}
          onReset={() => { setDraft(toDraft(settings)); setSaved(false); setError("") }}
          syncing={syncing}
          syncResult={syncResult}
          onSyncNow={syncNow}
        />
      ) : (
        <div className="text-xs text-zinc-500 py-3 text-center">{error || t("loading")}</div>
      )}
    </div>
  )
}
