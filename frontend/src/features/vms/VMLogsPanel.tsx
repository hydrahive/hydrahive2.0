import { useEffect, useRef, useState } from "react"
import { FileText, RefreshCw, X } from "lucide-react"
import type { VM } from "./types"
import { vmsApi } from "./api"

interface Props {
  vm: VM
  onClose: () => void
}

const POLL_MS = 2500

export function VMLogsPanel({ vm, onClose }: Props) {
  const [lines, setLines] = useState<string[]>([])
  const [exists, setExists] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const preRef = useRef<HTMLPreElement>(null)

  async function refresh() {
    try {
      setError(null)
      const r = await vmsApi.log(vm.vm_id, 500)
      setExists(r.exists)
      setLines(r.lines)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  useEffect(() => {
    void refresh()
    if (!autoRefresh) return
    const t = setInterval(refresh, POLL_MS)
    return () => clearInterval(t)
  }, [vm.vm_id, autoRefresh])

  useEffect(() => {
    if (preRef.current) preRef.current.scrollTop = preRef.current.scrollHeight
  }, [lines])

  return (
    <div className="fixed inset-y-0 right-0 z-30 w-full sm:w-[640px] bg-zinc-900 border-l border-white/[8%] shadow-2xl flex flex-col">
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/[6%]">
        <div className="flex items-center gap-2">
          <FileText size={18} className="text-violet-400" />
          <h2 className="text-lg font-bold text-white">QEMU-Log — {vm.name}</h2>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-[11px] text-zinc-400">
            <input type="checkbox" checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="accent-violet-500" />
            Auto
          </label>
          <button onClick={refresh} className="p-1.5 rounded text-zinc-400 hover:text-zinc-200" title="Aktualisieren">
            <RefreshCw size={13} />
          </button>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200"><X size={16} /></button>
        </div>
      </div>
      <div className="flex-1 overflow-hidden p-3">
        {!exists ? (
          <p className="text-sm text-zinc-500 text-center py-12">Noch keine Log-Datei — VM wurde noch nicht gestartet.</p>
        ) : (
          <pre ref={preRef}
            className="w-full h-full overflow-auto p-3 rounded-lg bg-zinc-950 border border-white/[6%] text-[11px] font-mono leading-relaxed text-zinc-300 whitespace-pre-wrap">
            {lines.length === 0 ? <span className="text-zinc-600">Log ist leer.</span> : lines.join("\n")}
          </pre>
        )}
      </div>
      {error && (
        <div className="px-5 py-2 border-t border-white/[6%] text-xs text-rose-300 bg-rose-500/10">{error}</div>
      )}
    </div>
  )
}
