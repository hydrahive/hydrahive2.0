import { useEffect, useRef, useState } from "react"
import { Disc, Trash2, Upload } from "lucide-react"
import type { ISO } from "./types"
import { uploadIso, vmsApi } from "./api"
import { formatBytes } from "./format"

interface Props {
  onClose: () => void
}

export function ISOLibraryPanel({ onClose }: Props) {
  const [isos, setIsos] = useState<ISO[]>([])
  const [progress, setProgress] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  async function refresh() {
    try { setIsos(await vmsApi.isos()) }
    catch (e) { setError(e instanceof Error ? e.message : String(e)) }
  }
  useEffect(() => { void refresh() }, [])

  async function handleUpload(file: File) {
    setError(null)
    setProgress(0)
    try {
      await uploadIso(file, setProgress)
      setProgress(null)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setProgress(null)
    }
  }

  async function handleDelete(filename: string) {
    if (!confirm(`ISO "${filename}" löschen?`)) return
    try { await vmsApi.isoDelete(filename); await refresh() }
    catch (e) { setError(e instanceof Error ? e.message : String(e)) }
  }

  return (
    <div className="fixed inset-y-0 right-0 z-30 w-full sm:w-[480px] bg-zinc-900 border-l border-white/[8%] shadow-2xl flex flex-col">
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/[6%]">
        <div className="flex items-center gap-2">
          <Disc size={18} className="text-violet-400" />
          <h2 className="text-lg font-bold text-white">ISO-Library</h2>
        </div>
        <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200 text-sm">Schließen</button>
      </div>
      <div className="px-5 py-4 border-b border-white/[6%]">
        <button onClick={() => fileRef.current?.click()}
          disabled={progress !== null}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-violet-500/15 hover:bg-violet-500/25 border border-violet-500/30 text-violet-200 text-sm font-medium disabled:opacity-40">
          <Upload size={14} /> {progress !== null ? `Upload ${progress}%` : "ISO hochladen"}
        </button>
        <input ref={fileRef} type="file" accept=".iso,application/x-iso9660-image"
          className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) void handleUpload(f); e.target.value = "" }} />
        {progress !== null && (
          <div className="mt-2 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
            <div className="h-full bg-violet-500 transition-all" style={{ width: `${progress}%` }} />
          </div>
        )}
        {error && <p className="text-xs text-rose-300 mt-2">{error}</p>}
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {isos.length === 0 ? (
          <p className="text-sm text-zinc-500 text-center py-12">Keine ISOs vorhanden.</p>
        ) : isos.map((iso) => (
          <div key={iso.filename}
            className="flex items-center gap-3 p-3 rounded-lg border border-white/[8%] bg-white/[2%]">
            <Disc size={16} className="text-zinc-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-zinc-100 truncate">{iso.filename}</p>
              <p className="text-[11px] text-zinc-500">{formatBytes(iso.size_bytes)}</p>
            </div>
            <button onClick={() => handleDelete(iso.filename)}
              className="p-1.5 rounded text-zinc-500 hover:text-rose-300 hover:bg-rose-500/10">
              <Trash2 size={13} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
