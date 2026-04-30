import { useRef, useState } from "react"
import { Download, Upload, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { systemApi } from "./api"
import { BackupRestoreModal, type RestoreState } from "./BackupRestoreModal"

export function BackupCard() {
  const { t } = useTranslation("system")
  const [state, setState] = useState<RestoreState>("idle")
  const [error, setError] = useState<string | null>(null)
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
    const f = e.target.files?.[0]
    if (!f) return
    pendingFile.current = f
    setError(null)
    setState("confirm")
    e.target.value = ""
  }

  async function confirmRestore() {
    const f = pendingFile.current
    if (!f) return
    setState("uploading")
    setError(null)
    try {
      await systemApi.restoreBackup(f)
      setState("waiting")
      const startedAt = Date.now()
      while (Date.now() - startedAt < 120_000) {
        await new Promise(r => setTimeout(r, 2000))
        try {
          const r = await fetch("/api/health", { cache: "no-store" })
          if (r.ok) {
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
    pendingFile.current = null
  }

  return (
    <div className="rounded-xl border border-white/[6%] bg-white/[2%] p-4 space-y-3">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
          {t("backup.title")}
        </p>
        <p className="text-zinc-300 text-sm mt-1">{t("backup.description")}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <button onClick={handleDownload} disabled={downloading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-300 text-xs font-medium hover:bg-white/[8%] disabled:opacity-50 transition-colors"
        >
          {downloading ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
          {t("backup.download")}
        </button>
        <button onClick={() => fileRef.current?.click()}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-300 text-xs font-medium hover:bg-white/[8%] transition-colors"
        >
          <Upload size={12} />
          {t("backup.restore")}
        </button>
        <input ref={fileRef} type="file" accept=".tar.gz,application/gzip"
          onChange={onFileSelected} className="hidden" />
      </div>
      {error && state === "idle" && (
        <p className="text-xs text-red-400 mt-2">{error}</p>
      )}
      {state !== "idle" && (
        <BackupRestoreModal state={state} error={error} fileName={pendingFile.current?.name}
          onConfirm={confirmRestore} onClose={close} />
      )}
    </div>
  )
}
