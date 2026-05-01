import { useEffect, useState } from "react"
import { AlertTriangle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { chatApi } from "./api"

interface Props {
  sessionId: string
  /** Bumping this number triggers a re-fetch (e.g. after a message was sent). */
  refresh: number
}

interface TokenInfo {
  used: number
  context_window: number
  compact_threshold: number
}

export function TokenMeter({ sessionId, refresh }: Props) {
  const { t, i18n } = useTranslation("chat")
  const [info, setInfo] = useState<TokenInfo | null>(null)

  useEffect(() => {
    chatApi.tokens(sessionId).then(setInfo).catch(() => setInfo(null))
  }, [sessionId, refresh])

  if (!info || info.context_window === 0) return null

  const pct = info.compact_threshold > 0 ? Math.min(100, (info.used / info.compact_threshold) * 100) : 0
  const tone =
    pct < 50 ? "text-zinc-500"
      : pct < 80 ? "text-amber-400"
      : "text-rose-400"
  const barTone =
    pct < 50 ? "bg-zinc-600"
      : pct < 80 ? "bg-amber-400"
      : "bg-rose-400"

  const fmt = (n: number) => n.toLocaleString(i18n.language)

  const warning = pct >= 90

  return (
    <div className="flex items-center gap-2" title={t("tokens.limit_tooltip", { limit: fmt(info.compact_threshold) })}>
      <div className="w-20 h-1 bg-white/[6%] rounded-full overflow-hidden">
        <div className={`h-full ${barTone} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-[11px] font-mono tabular-nums ${tone}`}>
        {fmt(info.used)} / {fmt(info.compact_threshold)}
      </span>
      {warning && (
        <span
          className="flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-amber-500/[10%] border border-amber-500/30 text-[10px] text-amber-300"
          title={t("tokens.compact_imminent_tooltip")}
        >
          <AlertTriangle size={10} /> {t("tokens.compact_imminent")}
        </span>
      )}
    </div>
  )
}
