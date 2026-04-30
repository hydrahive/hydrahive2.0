import { useEffect, useState } from "react"
import { RefreshCw } from "lucide-react"
import { containersApi } from "./api"

interface Props {
  containerId: string
}

export function ContainerConfigPane({ containerId }: Props) {
  const [text, setText] = useState<string>("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const r = await containersApi.config(containerId)
      setText(r.text || "(leer)")
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() /* eslint-disable-next-line */ }, [containerId])

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/[8%] flex-shrink-0">
        <p className="text-xs text-zinc-400">incus config show</p>
        <button onClick={load} disabled={loading}
          className="p-1.5 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-400 hover:text-zinc-200 disabled:opacity-40">
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
        </button>
      </div>
      {error && (
        <div className="px-4 py-2 bg-rose-500/10 border-b border-rose-500/30 text-xs text-rose-200 flex-shrink-0">{error}</div>
      )}
      <pre className="flex-1 min-h-0 overflow-auto p-3 text-[11px] text-zinc-300 font-mono whitespace-pre-wrap bg-[#0b0b0f]">{text}</pre>
    </div>
  )
}
