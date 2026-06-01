import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { RefreshCw } from "lucide-react"
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
      const r = await containersApi.log(containerId)
      setText(r.text || t("logs.empty"))
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [containerId])

  useEffect(() => { void load() }, [load])

  useEffect(() => {
    if (!auto) return
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [auto, load])

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex items-center justify-between px-4 py-2 border-b border-white/[8%] flex-shrink-0">
        <p className="text-xs text-zinc-400">{t("logs.lifecycle_title")}</p>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-[11px] text-zinc-400">
            <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)}
              className="accent-violet-500" />
            {t("logs.auto_refresh")}
          </label>
          <button onClick={load} disabled={loading}
            className="p-1.5 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-400 hover:text-zinc-200 disabled:opacity-40">
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>
      {error && (
        <div className="px-4 py-2 bg-rose-500/10 border-b border-rose-500/30 text-xs text-rose-200 flex-shrink-0">{error}</div>
      )}
      <pre className="flex-1 min-h-0 overflow-auto p-3 text-[11px] text-zinc-300 font-mono whitespace-pre-wrap break-all bg-[#0b0b0f]">{text}</pre>
    </div>
  )
}
