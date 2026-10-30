import { useCallback, useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { RefreshCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminOverlay } from "@/features/cockpit/admin/AdminOverlay"
import { AdminAction, AdminTabs } from "@/features/cockpit/admin/ui"
import { systemApi } from "@/features/system/api"
import { archiveApi, cleanupSelection, type ArchiveEntry, type ArchiveKind, type ArchiveStatus, type OrphanScan } from "./api"
import { archiveTabs, parseArchiveTab, type ArchiveTab } from "./archiveTabs"
import { ArchiveView } from "./ArchiveView"
import { DropLocalDialog, type DropSelection } from "./DropLocalDialog"
import { MoveDialog } from "./MoveDialog"
import { useRemote } from "./useRemote"
import { TrashConfirmDialog } from "./TrashConfirmDialog"
import { ADMIN_OVERLAY_THEME } from "@/shared/brand/boxThemes"

/** Admin-Fenster „Archiv & Sicherung“ (docs/specs/archiv-system.md, Etappe 1). */
export function ArchiveOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("archive")
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = parseArchiveTab(searchParams.get("tab"))
  function selectTab(next: ArchiveTab) {
    const params = new URLSearchParams(searchParams)
    params.set("tab", next)
    setSearchParams(params, { replace: true })
  }
  const [status, setStatus] = useState<ArchiveStatus | null>(null)
  const [entries, setEntries] = useState<ArchiveEntry[]>([])
  const [kind, setKind] = useState<ArchiveKind | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [confirmTrash, setConfirmTrash] = useState(false)
  const [shareBusy, setShareBusy] = useState(false)
  const [moveOpen, setMoveOpen] = useState(false)
  const [orphans, setOrphans] = useState<OrphanScan | null>(null)
  const [orphansBusy, setOrphansBusy] = useState(false)
  const [cleanupJobs, setCleanupJobs] = useState<string[]>([])
  const [drop, setDrop] = useState<DropSelection | null>(null)
  const working = !!status?.move?.running || !!status?.jobs?.running || !!status?.jobs?.queued.length

  const reload = useCallback(async () => {
    try {
      const [s, e] = await Promise.all([archiveApi.status(), archiveApi.entries(kind)])
      setStatus(s); setEntries(e.entries); setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : t("load_failed"))
    }
  }, [kind, t])

  useEffect(() => {
    const first = setTimeout(() => { void reload() }, 0)
    return () => clearTimeout(first)
  }, [reload])

  const remote = useRemote(status?.remote, reload)

  // Waisen nur beim Öffnen und nach dem Aufräumen zählen – das Zählen ist teurer als der Status.
  const loadOrphans = useCallback(async () => {
    try { setOrphans(await archiveApi.orphans()) }
    catch (err) { setError(err instanceof Error ? err.message : t("load_failed")) }
  }, [t])

  useEffect(() => {
    const first = setTimeout(() => { void loadOrphans() }, 0)
    return () => clearTimeout(first)
  }, [loadOrphans])

  async function cleanupOrphans() {
    if (!orphans) return
    setOrphansBusy(true)
    try {
      const { job_ids } = await archiveApi.cleanupOrphans(cleanupSelection(orphans))
      setCleanupJobs(job_ids); setOrphans(null); await reload()
    }
    catch (err) { setError(err instanceof Error ? err.message : t("orphans.cleanup_failed")) }
    finally { setOrphansBusy(false) }
  }

  // Nach dem Aufräumen erst neu zählen, wenn alle eigenen Aufträge fertig gemeldet sind – nicht, wenn die
  // Reihe nur gerade leer aussieht (ein schneller Auftrag ist fertig, bevor die erste Abfrage kommt).
  const cleanupDone = cleanupJobs.length > 0 && cleanupJobs.every((id) => status?.jobs?.done.some((j) => j.id === id))
  useEffect(() => {
    if (cleanupJobs.length === 0) return
    if (!cleanupDone) {
      const poll = setTimeout(() => { void reload() }, 1000)
      return () => clearTimeout(poll)
    }
    const later = setTimeout(() => { setCleanupJobs([]); void loadOrphans() }, 0)
    return () => clearTimeout(later)
  }, [cleanupJobs, cleanupDone, status, reload, loadOrphans])

  // Während eines Umzugs oder Lösch-Auftrags den Fortschritt abfragen (läuft im Dienst, nicht im Browser).
  useEffect(() => {
    if (!working) return
    const timer = setInterval(() => { void reload() }, 1500)
    return () => clearInterval(timer)
  }, [working, reload])

  async function setupSamba() {
    setShareBusy(true)
    try {
      await systemApi.sambaSetup(); setError(null)
      // Installation läuft im Hintergrund; danach legt HydraHive die Freigabe beim nächsten Status selbst an.
      for (let i = 0; i < 150; i++) {
        await new Promise((resolve) => setTimeout(resolve, 2000))
        const next = await archiveApi.status()
        setStatus(next)
        if (next.share.samba_installed && next.share.samba_running) break
      }
    } catch (err) { setError(err instanceof Error ? err.message : t("share.setup_failed")) }
    finally { setShareBusy(false) }
  }

  async function switchShare(enabled: boolean) {
    setShareBusy(true)
    try { await archiveApi.setShare(enabled); await reload() }
    catch (err) { setError(err instanceof Error ? err.message : t("share.switch_failed")) }
    finally { setShareBusy(false) }
  }

  return (
    <AdminOverlay theme={ADMIN_OVERLAY_THEME["archive"]}
      eyebrow="Admin · Wartung"
      title={t("title")}
      onClose={onClose}
      maxWidthClass="max-w-4xl"
      headerActions={(
        <AdminAction tone="ghost" onClick={() => void reload()} aria-label={t("reload")} title={t("reload")}>
          <RefreshCw size={12} />
        </AdminAction>
      )}
    >
      <div className="space-y-3 p-4">
        <p className="text-sm text-[#9aa7bc]">{t("subtitle")}</p>
        <AdminTabs label={t("title")} idPrefix="archive" active={tab} onSelect={selectTab}
          tabs={archiveTabs(status, orphans, entries.length, t)}>
        <ArchiveView
          tab={tab}
          status={status}
          entries={entries}
          host={window.location.hostname}
          kind={kind}
          error={error}
          shareBusy={shareBusy}
          onKind={setKind}
          onEmptyTrash={() => setConfirmTrash(true)}
          onSetupSamba={() => void setupSamba()}
          onShareSwitch={(enabled) => void switchShare(enabled)}
          onChangeLocation={() => setMoveOpen(true)}
          remote={{ ...remote, onDropAll: () => setDrop({ all: true }) }}
          onDropLocal={(e) => setDrop({ paths: [e.path], bytes: e.size })}
          orphans={orphans}
          orphansBusy={orphansBusy || working || cleanupJobs.length > 0}
          onCleanupOrphans={() => void cleanupOrphans()}
        />
        </AdminTabs>
      </div>
      {drop && status?.remote && (
        <DropLocalDialog remote={status.remote} selection={drop} onClose={() => setDrop(null)}
          onStarted={() => { setDrop(null); void reload() }} />
      )}
      {moveOpen && (
        <MoveDialog onClose={() => setMoveOpen(false)} onStarted={() => { setMoveOpen(false); void reload() }} />
      )}
      {confirmTrash && status && (
        <TrashConfirmDialog
          trashBytes={status.storage.trash_bytes}
          onClose={() => setConfirmTrash(false)}
          onDone={() => { setConfirmTrash(false); void reload() }}
        />
      )}
    </AdminOverlay>
  )
}
