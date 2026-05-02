import { useRef, useState } from "react"
import { Download, RotateCcw } from "lucide-react"
import { useTranslation } from "react-i18next"
import { profileApi } from "./api"

export function BackupRestoreCard() {
  const { t } = useTranslation("profile")
  const [downloading, setDownloading] = useState(false)
  const [restoring, setRestoring] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  async function handleDownload() {
    setDownloading(true)
    setError(null)
    try {
      const res = await profileApi.downloadBackup()
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      const cd = res.headers.get("content-disposition") ?? ""
      const match = cd.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      const filename = match?.[1]?.replace(/['"]/g, "") ?? "backup.tar.gz"
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setDownloading(false)
    }
  }

  async function handleFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ""
    if (!window.confirm(t("backup.restore_confirm"))) return

    setRestoring(true)
    setError(null)
    setDone(false)
    try {
      await profileApi.restoreBackup(file)
      setDone(true)
      setTimeout(() => setDone(false), 3000)
    } catch (e: any) {
      const msg = e?.detail ?? e?.message ?? String(e)
      setError(t("backup.error", { msg }))
    } finally {
      setRestoring(false)
    }
  }

  return (
    <div className="rounded-xl border border-white/[8%] bg-white/[2%] p-5 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-zinc-200">{t("backup.title")}</h2>
        <p className="text-xs text-zinc-500 mt-0.5">{t("backup.description")}</p>
      </div>

      {error && (
        <p className="text-xs text-rose-400 rounded border border-rose-500/20 bg-rose-500/[6%] px-3 py-2">{error}</p>
      )}
      {done && (
        <p className="text-xs text-emerald-400">{t("backup.restore_done")}</p>
      )}

      <div className="flex gap-2">
        <button
          onClick={handleDownload}
          disabled={downloading || restoring}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs border border-white/[8%] text-zinc-300 hover:text-white hover:bg-white/[5%] transition-colors disabled:opacity-30"
        >
          <Download size={12} />
          {downloading ? t("backup.downloading") : t("backup.download")}
        </button>

        <button
          onClick={() => fileRef.current?.click()}
          disabled={downloading || restoring}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs border border-white/[8%] text-zinc-300 hover:text-white hover:bg-white/[5%] transition-colors disabled:opacity-30"
        >
          <RotateCcw size={12} />
          {restoring ? t("backup.restoring") : t("backup.restore")}
        </button>
      </div>

      <input
        ref={fileRef}
        type="file"
        accept=".tar.gz,.gz"
        className="hidden"
        onChange={handleFileSelected}
      />
    </div>
  )
}
