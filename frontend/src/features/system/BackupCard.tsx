import { useRef, useState } from "react"
import { Download, HardDriveDownload, Loader2, Upload } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminFeedback, AdminPanel } from "@/features/cockpit/admin/ui"
import { systemApi } from "./api"
import { BackupRestoreModal, type RestoreState } from "./BackupRestoreModal"

export function BackupCard() {
  const { t } = useTranslation("system")
  const [state, setState] = useState<RestoreState>("idle")
  const [error, setError] = useState<string | null>(null)
  const [selectedFileName, setSelectedFileName] = useState<string>()
  const [downloading, setDownloading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const pendingFile = useRef<File | null>(null)

  async function handleDownload() {
    setDownloading(true)
    try {
      await systemApi.downloadBackup()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setDownloading(false)
    }
  }

  function onFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    pendingFile.current = file
    setSelectedFileName(file.name)
    setError(null)
    setState("confirm")
    e.target.value = ""
  }

  async function confirmRestore() {
    const file = pendingFile.current
    if (!file) return
    setState("uploading")
    setError(null)
    try {
      await systemApi.restoreBackup(file)
      setState("waiting")
      const startedAt = Date.now()
      while (Date.now() - startedAt < 120_000) {
        await new Promise((resolve) => setTimeout(resolve, 2000))
        try {
          const response = await fetch("/api/health", { cache: "no-store" })
          if (response.ok) {
            setState("done")
            return
          }
        } catch { /* still restarting */ }
      }
      setState("done")
    } catch (e) {
      setState("failed")
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  function close() {
    setState("idle")
    setSelectedFileName(undefined)
    pendingFile.current = null
  }

  return (
    <AdminPanel
      title={t("backup.title")}
      description={t("backup.description")}
      icon={HardDriveDownload}
      bodyClassName="space-y-3"
    >
      <div className="flex flex-wrap gap-2">
        <AdminAction onClick={handleDownload} disabled={downloading} tone="primary">
          {downloading ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
          {t("backup.download")}
        </AdminAction>
        <AdminAction onClick={() => fileRef.current?.click()}>
          <Upload size={12} />
          {t("backup.restore")}
        </AdminAction>
        <input
          ref={fileRef}
          type="file"
          accept=".tar.gz,application/gzip"
          onChange={onFileSelected}
          className="hidden"
        />
      </div>
      {error && state === "idle" && <AdminFeedback tone="danger">{error}</AdminFeedback>}
      {state !== "idle" && (
        <BackupRestoreModal
          state={state}
          error={error}
          fileName={selectedFileName}
          onConfirm={confirmRestore}
          onClose={close}
        />
      )}
    </AdminPanel>
  )
}
