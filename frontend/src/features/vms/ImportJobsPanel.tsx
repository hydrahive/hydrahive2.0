import { useEffect, useRef, useState } from "react"
import { Download, Upload, X } from "lucide-react"
import type { ImportJob } from "./types"
import { uploadImport, vmsApi } from "./api"
import { ImportJobCard } from "./_ImportJobCard"

interface Props {
  onClose: () => void
}

const POLL_MS = 2000

export function ImportJobsPanel({ onClose }: Props) {
  const [jobs, setJobs] = useState<ImportJob[]>([])
  const [error, setError] = useState<string | null>(null)
  const [uploadPct, setUploadPct] = useState<number | null>(null)
  const [pathInput, setPathInput] = useState("")
  const [busy, setBusy] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  async function refresh() {
    try { setJobs(await vmsApi.importJobs()) }
    catch (e) { setError(e instanceof Error ? e.message : String(e)) }
  }
  useEffect(() => {
    void refresh()
    const t = setInterval(refresh, POLL_MS)
    return () => clearInterval(t)
  }, [])

  async function handleUpload(file: File) {
    setUploadPct(0); setError(null)
    try {
      await uploadImport(file, setUploadPct)
      setUploadPct(null)
      await refresh()
    } catch (e) {
      setUploadPct(null)
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  async function handleFromPath() {
    if (!pathInput.trim()) return
    setBusy(true); setError(null)
    try {
      await vmsApi.importFromPath(pathInput.trim())
      setPathInput("")
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally { setBusy(false) }
  }

  async function handleDelete(j: ImportJob) {
    if (!confirm(`Job "${j.job_id.slice(0,8)}…" löschen?${j.status === "done" ? " (qcow2 wird mitgelöscht falls nicht von VM verwendet)" : ""}`)) return
    try {
      await vmsApi.importJobDelete(j.job_id)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <div className="fixed inset-y-0 right-0 z-30 w-full sm:w-[560px] bg-zinc-900 border-l border-white/[8%] shadow-2xl flex flex-col">
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/[6%]">
        <div className="flex items-center gap-2">
          <Download size={18} className="text-violet-400" />
          <h2 className="text-lg font-bold text-white">Disk-Import</h2>
        </div>
        <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200"><X size={16} /></button>
      </div>

      <div className="px-5 py-4 border-b border-white/[6%] space-y-3">
        <button onClick={() => fileRef.current?.click()} disabled={uploadPct !== null}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-violet-500/15 hover:bg-violet-500/25 border border-violet-500/30 text-violet-200 text-sm disabled:opacity-30">
          <Upload size={14} /> {uploadPct !== null ? `Upload ${uploadPct}%` : "Disk-Image hochladen (qcow2/raw/vmdk/vdi)"}
        </button>
        <input ref={fileRef} type="file" className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) void handleUpload(f); e.target.value = "" }} />
        {uploadPct !== null && (
          <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
            <div className="h-full bg-violet-500 transition-all" style={{ width: `${uploadPct}%` }} />
          </div>
        )}

        <div className="flex gap-2">
          <input value={pathInput} onChange={(e) => setPathInput(e.target.value)}
            disabled={busy} placeholder="Server-Pfad zu existierender Disk (Admin only, z.B. /tmp/disk.qcow2)"
            className="flex-1 bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-xs text-zinc-200 disabled:opacity-50 focus:border-violet-500/50 outline-none" />
          <button onClick={handleFromPath} disabled={busy || !pathInput.trim()}
            className="px-3 py-2 rounded-lg bg-white/[5%] border border-white/[8%] hover:bg-white/[10%] text-xs text-zinc-300 disabled:opacity-30">
            Importieren
          </button>
        </div>

        {error && <div className="text-xs text-rose-300 bg-rose-500/10 border border-rose-500/20 rounded-md px-3 py-2">{error}</div>}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {jobs.length === 0 ? (
          <p className="text-sm text-zinc-500 text-center py-12">Keine Import-Jobs.</p>
        ) : jobs.map((j) => (
          <ImportJobCard key={j.job_id} job={j} onDelete={() => handleDelete(j)} />
        ))}
      </div>
    </div>
  )
}

