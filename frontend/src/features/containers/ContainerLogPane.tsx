import { useCallback, useEffect, useState } from "react"
import { RefreshCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import {
  AdminAction,
  AdminCodeBlock,
  AdminFeedback,
  AdminToggle,
} from "@/features/cockpit/admin/ui"
import { containersApi } from "./api"

interface Props {
  containerId: string
}

export function ContainerLogPane({ containerId }: Props) {
  const { t } = useTranslation("containers")
  const [text, setText] = useState<string>("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [auto, setAuto] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const response = await containersApi.log(containerId)
      setText(response.text || t("logs.empty"))
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setLoading(false)
    }
  }, [containerId, t])

  useEffect(() => {
    const initial = window.setTimeout(load, 0)
    return () => window.clearTimeout(initial)
  }, [load])

  useEffect(() => {
    if (!auto) return
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [auto, load])

  return (
    <div className="flex h-full min-h-0 flex-col bg-[#0e1420]">
      <div className="flex shrink-0 items-center justify-between border-b border-[#2a364b] bg-[#131b2a] px-4 py-2">
        <p className="text-xs text-[#8d9ab0]">{t("logs.lifecycle_title")}</p>
        <div className="flex items-center gap-2">
          <AdminToggle label={t("logs.auto_refresh")} checked={auto} onChange={(event) => setAuto(event.target.checked)} />
          <AdminAction onClick={load} disabled={loading} aria-label="Logs neu laden" title="Logs neu laden" className="px-2 py-1.5">
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          </AdminAction>
        </div>
      </div>
      {error && <AdminFeedback tone="danger" className="m-3 shrink-0">{error}</AdminFeedback>}
      <AdminCodeBlock className="min-h-0 flex-1 break-all rounded-none border-0">{text}</AdminCodeBlock>
    </div>
  )
}
