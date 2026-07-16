import { useCallback, useEffect, useState } from "react"
import { RefreshCw } from "lucide-react"
import { AdminAction, AdminCodeBlock, AdminFeedback } from "@/features/cockpit/admin/ui"
import { containersApi } from "./api"

interface Props {
  containerId: string
}

export function ContainerConfigPane({ containerId }: Props) {
  const [text, setText] = useState<string>("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const response = await containersApi.config(containerId)
      setText(response.text || "(leer)")
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setLoading(false)
    }
  }, [containerId])

  useEffect(() => {
    const initial = window.setTimeout(load, 0)
    return () => window.clearTimeout(initial)
  }, [load])

  return (
    <div className="flex h-full min-h-0 flex-col bg-[#0e1420]">
      <div className="flex shrink-0 items-center justify-between border-b border-[#2a364b] bg-[#131b2a] px-4 py-2">
        <p className="font-mono text-xs text-[#8d9ab0]">incus config show</p>
        <AdminAction onClick={load} disabled={loading} aria-label="Konfiguration neu laden" title="Konfiguration neu laden" className="px-2 py-1.5">
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
        </AdminAction>
      </div>
      {error && <AdminFeedback tone="danger" className="m-3 shrink-0">{error}</AdminFeedback>}
      <AdminCodeBlock className="min-h-0 flex-1 rounded-none border-0">{text}</AdminCodeBlock>
    </div>
  )
}
